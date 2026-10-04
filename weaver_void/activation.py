"""VOID neural capability donor adapter for Weaver OS.

This module deliberately owns no authority and no persistent ledger. It consumes
cryptographically verified authority from ``triadic_controls`` and produces a
bounded activation evidence object suitable for later binding into the canonical
receipt/Chronicle path.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol

from triadic_controls.crypto.verifier import VerificationResult

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    MALFORMED_IDENTITY = "MALFORMED_IDENTITY"
    AUTHORITY_INVALID = "AUTHORITY_INVALID"
    AUTHORITY_BINDING_MISMATCH = "AUTHORITY_BINDING_MISMATCH"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    BACKEND_FAILED = "BACKEND_FAILED"
    RESULT_IDENTITY_MISMATCH = "RESULT_IDENTITY_MISMATCH"
    RETENTION_GATE_FAILED = "RETENTION_GATE_FAILED"


@dataclass(frozen=True)
class ActivationIntent:
    request_id: str
    model_id: str
    backend_id: str
    action: ActivationAction
    checkpoint_sha256: str
    input_sha256: str
    retention_floor: float | None = None

    def authority_binding(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "backend_id": self.backend_id,
            "action": self.action.value,
            "checkpoint_sha256": self.checkpoint_sha256,
            "input_sha256": self.input_sha256,
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


@dataclass(frozen=True)
class ActivationEvidence:
    status: ActivationStatus
    request_id: str
    authority_event_type: str
    authority_payload_sha256: str
    intent_sha256: str
    result_sha256: str | None
    checkpoint_sha256: str
    primary_metric: float | None
    retention_metric: float | None
    reject_code: str | None
    authority_delta: int = 0


class AuthorityVerifier(Protocol):
    def verify_authority_token(
        self,
        envelope: dict[str, Any],
        requested_level: int,
        inner_payload: dict[str, Any] | None = None,
    ) -> VerificationResult: ...


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


def build_activation_authority_payload(
    intent: ActivationIntent,
    *,
    authority_level: int,
    system_id: str = "weaver-neural-runtime",
) -> dict[str, Any]:
    """Build the payload that must be signed and verified before activation.

    The exact activation tuple lives inside the signed payload, so a valid token
    for one request/model/checkpoint cannot be silently reused for another.
    """

    return {
        "token_id": intent.request_id,
        "system_id": system_id,
        "authority_level": authority_level,
        "scope": {
            "task": "neural_activation",
            "region": intent.model_id,
            "activation": intent.authority_binding(),
        },
    }


class VoidActivationAdapter:
    """Bounded capability adapter below Weaver's authority boundary.

    The adapter verifies the signed authority token itself, checks that the token
    binds the exact activation tuple, prevents process-local duplicate handoff,
    invokes the backend, and returns evidence. It never grants or promotes
    authority: ``authority_delta`` is always zero.

    Durable exactly-once semantics remain a higher-level execution-boundary
    responsibility; the in-memory request set here is defense in depth only.
    """

    def __init__(
        self,
        verifier: AuthorityVerifier,
        *,
        system_id: str = "weaver-neural-runtime",
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
        malformed = not (
            intent.request_id
            and intent.model_id
            and intent.backend_id
            and _SHA256_RE.fullmatch(intent.checkpoint_sha256)
            and _SHA256_RE.fullmatch(intent.input_sha256)
        )
        if malformed:
            return self._reject(intent, authority_payload, ActivationRejectCode.MALFORMED_IDENTITY)

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

        # Consume before backend invocation: a failed backend may be retried only
        # under a fresh authorization/request identity.
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

        if intent.retention_floor is not None and (
            result.retention_metric is None or result.retention_metric < intent.retention_floor
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
        return (
            result.request_id == intent.request_id
            and result.model_id == intent.model_id
            and result.backend_id == intent.backend_id
            and result.checkpoint_sha256 == intent.checkpoint_sha256
            and bool(_SHA256_RE.fullmatch(result.output_sha256))
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
            authority_event_type=authority_event_type,
            authority_payload_sha256=_sha256_json(authority_payload),
            intent_sha256=_sha256_json(intent_data),
            result_sha256=_sha256_json(asdict(result)) if result is not None else None,
            checkpoint_sha256=intent.checkpoint_sha256,
            primary_metric=result.primary_metric if result is not None else None,
            retention_metric=result.retention_metric if result is not None else None,
            reject_code=reject_code,
            authority_delta=0,
        )
