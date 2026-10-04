"""Weaver-owned activation contract and admission boundary.

This module separates capability from authority. A backend may compute, train,
evaluate, save, or load only after the existing Weaver authority verifier admits
an exact, versioned activation contract. Evidence produced here never mints
authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol

from triadic_controls.crypto.verifier import VerificationResult

CONTRACT_VERSION = "weaver-activation-contract-1"
DEFAULT_SYSTEM_ID = "weaver-activation-runtime"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


class ActivationAction(str, Enum):
    INFER = "infer"
    TRAIN = "train"
    EVALUATE = "evaluate"
    SAVE_CHECKPOINT = "save_checkpoint"
    LOAD_CHECKPOINT = "load_checkpoint"


class ActivationStatus(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"


class ActivationRejectCode(str, Enum):
    CONTRACT_VERSION_MISMATCH = "CONTRACT_VERSION_MISMATCH"
    MALFORMED_IDENTITY = "MALFORMED_IDENTITY"
    AUTHORITY_INVALID = "AUTHORITY_INVALID"
    AUTHORITY_BINDING_MISMATCH = "AUTHORITY_BINDING_MISMATCH"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    BACKEND_FAILED = "BACKEND_FAILED"
    RESULT_IDENTITY_MISMATCH = "RESULT_IDENTITY_MISMATCH"
    METRIC_INVALID = "METRIC_INVALID"
    RETENTION_GATE_FAILED = "RETENTION_GATE_FAILED"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _valid_digest(value: str | None, *, optional: bool = False) -> bool:
    if value is None:
        return optional
    return bool(_SHA256_RE.fullmatch(value))


def _valid_id(value: str) -> bool:
    return bool(_ID_RE.fullmatch(value))


def _valid_metric(value: float | None) -> bool:
    if value is None:
        return True
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class ActivationIntent:
    request_id: str
    model_id: str
    backend_id: str
    action: ActivationAction
    checkpoint_sha256: str
    input_sha256: str
    backend_sha256: str | None = None
    retention_floor: float | None = None
    contract_version: str = CONTRACT_VERSION

    def contract_material(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "model_id": self.model_id,
            "backend_id": self.backend_id,
            "backend_sha256": self.backend_sha256,
            "action": self.action.value,
            "checkpoint_sha256": self.checkpoint_sha256,
            "input_sha256": self.input_sha256,
            "retention_floor": self.retention_floor,
        }

    def contract_sha256(self) -> str:
        return _sha256_json(self.contract_material())

    def authority_binding(self) -> dict[str, Any]:
        return {
            **self.contract_material(),
            "contract_sha256": self.contract_sha256(),
        }


@dataclass(frozen=True)
class BackendActivationResult:
    request_id: str
    model_id: str
    backend_id: str
    checkpoint_sha256: str
    output_sha256: str
    primary_metric: float | None = None
    retention_metric: float | None = None
    backend_sha256: str | None = None
    contract_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class ActivationEvidence:
    status: ActivationStatus
    request_id: str
    contract_version: str
    contract_sha256: str
    authority_event_type: str
    authority_payload_sha256: str
    intent_sha256: str
    result_sha256: str | None
    checkpoint_sha256: str
    primary_metric: float | None
    retention_metric: float | None
    reject_code: str | None
    backend_sha256: str | None = None
    authority_delta: int = 0


class AuthorityVerifier(Protocol):
    def verify_authority_token(
        self,
        envelope: dict[str, Any],
        requested_level: int,
        inner_payload: dict[str, Any] | None = None,
    ) -> VerificationResult: ...


def build_activation_authority_payload(
    intent: ActivationIntent,
    *,
    authority_level: int,
    system_id: str = DEFAULT_SYSTEM_ID,
) -> dict[str, Any]:
    """Build the exact versioned activation contract that must be signed."""
    return {
        "token_id": intent.request_id,
        "system_id": system_id,
        "authority_level": authority_level,
        "scope": {
            "task": "weaver_activation",
            "region": intent.model_id,
            "activation": intent.authority_binding(),
        },
    }


class WeaverActivationAdapter:
    """Fail-closed admission layer between Weaver authority and a backend."""

    def __init__(
        self,
        verifier: AuthorityVerifier,
        *,
        system_id: str = DEFAULT_SYSTEM_ID,
    ) -> None:
        self._verifier = verifier
        self._system_id = system_id
        self._consumed_request_ids: set[str] = set()

    def execute(
        self,
        intent: ActivationIntent,
        *,
        authority_envelope: dict[str, Any],
        authority_payload: dict[str, Any],
        requested_level: int,
        backend: Callable[[ActivationIntent], BackendActivationResult],
    ) -> ActivationEvidence:
        if intent.contract_version != CONTRACT_VERSION:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.CONTRACT_VERSION_MISMATCH,
            )

        retention_floor_valid = (
            intent.retention_floor is None
            or (
                _valid_metric(intent.retention_floor)
                and 0.0 <= intent.retention_floor <= 1.0
            )
        )
        identity_valid = (
            _valid_id(intent.request_id)
            and _valid_id(intent.model_id)
            and _valid_id(intent.backend_id)
            and _valid_digest(intent.checkpoint_sha256)
            and _valid_digest(intent.input_sha256)
            and _valid_digest(intent.backend_sha256, optional=True)
            and retention_floor_valid
        )
        if not identity_valid:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.MALFORMED_IDENTITY,
            )

        verification = self._verifier.verify_authority_token(
            authority_envelope,
            requested_level=requested_level,
            inner_payload=authority_payload,
        )
        if not verification.is_valid:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.AUTHORITY_INVALID,
                authority_event_type=verification.ledger_event_type,
            )

        expected_payload = build_activation_authority_payload(
            intent,
            authority_level=requested_level,
            system_id=self._system_id,
        )
        if authority_payload != expected_payload:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.AUTHORITY_BINDING_MISMATCH,
                authority_event_type=verification.ledger_event_type,
            )

        if intent.request_id in self._consumed_request_ids:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.DUPLICATE_REQUEST,
                authority_event_type=verification.ledger_event_type,
            )

        self._consumed_request_ids.add(intent.request_id)
        try:
            result = backend(intent)
        except Exception:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.BACKEND_FAILED,
                authority_event_type=verification.ledger_event_type,
            )

        if not self._result_matches_intent(intent, result):
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.RESULT_IDENTITY_MISMATCH,
                authority_event_type=verification.ledger_event_type,
                result=result,
            )

        if not _valid_metric(result.primary_metric) or not _valid_metric(result.retention_metric):
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.METRIC_INVALID,
                authority_event_type=verification.ledger_event_type,
                result=result,
            )
        if result.retention_metric is not None and not 0.0 <= result.retention_metric <= 1.0:
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.METRIC_INVALID,
                authority_event_type=verification.ledger_event_type,
                result=result,
            )

        if intent.retention_floor is not None and (
            result.retention_metric is None
            or result.retention_metric < intent.retention_floor
        ):
            return self._reject(
                intent,
                authority_payload,
                ActivationRejectCode.RETENTION_GATE_FAILED,
                authority_event_type=verification.ledger_event_type,
                result=result,
            )

        return self._evidence(
            intent,
            authority_payload,
            status=ActivationStatus.PASS,
            authority_event_type=verification.ledger_event_type,
            result=result,
            reject_code=None,
        )

    @staticmethod
    def _result_matches_intent(
        intent: ActivationIntent, result: BackendActivationResult
    ) -> bool:
        backend_digest_matches = intent.backend_sha256 is None or (
            result.backend_sha256 == intent.backend_sha256
        )
        return (
            result.contract_version == intent.contract_version
            and result.request_id == intent.request_id
            and result.model_id == intent.model_id
            and result.backend_id == intent.backend_id
            and result.checkpoint_sha256 == intent.checkpoint_sha256
            and _valid_digest(result.output_sha256)
            and backend_digest_matches
        )

    def _reject(
        self,
        intent: ActivationIntent,
        authority_payload: Mapping[str, Any],
        code: ActivationRejectCode,
        *,
        authority_event_type: str = "NOT_VERIFIED",
        result: BackendActivationResult | None = None,
    ) -> ActivationEvidence:
        return self._evidence(
            intent,
            authority_payload,
            status=ActivationStatus.REJECT,
            authority_event_type=authority_event_type,
            result=result,
            reject_code=code.value,
        )

    @staticmethod
    def _evidence(
        intent: ActivationIntent,
        authority_payload: Mapping[str, Any],
        *,
        status: ActivationStatus,
        authority_event_type: str,
        result: BackendActivationResult | None,
        reject_code: str | None,
    ) -> ActivationEvidence:
        intent_data = asdict(intent)
        intent_data["action"] = intent.action.value
        return ActivationEvidence(
            status=status,
            request_id=intent.request_id,
            contract_version=intent.contract_version,
            contract_sha256=intent.contract_sha256(),
            authority_event_type=authority_event_type,
            authority_payload_sha256=_sha256_json(authority_payload),
            intent_sha256=_sha256_json(intent_data),
            result_sha256=_sha256_json(asdict(result)) if result is not None else None,
            checkpoint_sha256=intent.checkpoint_sha256,
            primary_metric=result.primary_metric if result is not None else None,
            retention_metric=result.retention_metric if result is not None else None,
            reject_code=reject_code,
            backend_sha256=(
                result.backend_sha256 if result is not None else intent.backend_sha256
            ),
            authority_delta=0,
        )
