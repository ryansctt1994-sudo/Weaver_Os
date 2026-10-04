"""Canonical Weaver activation receipt.

The receipt is derived from ActivationEvidence. It binds admitted artifacts and
the exact rejected/accepted intent hashes without pretending unavailable values
were verified. PASS receipts require complete artifact digests; REJECT receipts
may contain null artifact fields when rejection occurred before admission.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Literal

from .activation import ActivationEvidence, ActivationStatus

RECEIPT_SCHEMA_VERSION = "weaver-activation-receipt-1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _digest_or_none(value: str | None) -> str | None:
    return value if value is not None and _SHA256_RE.fullmatch(value) else None


def _finite_metric(value: float | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class ActivationReceipt:
    schema_version: str
    request_id: str
    model_id: str
    backend_id: str
    contract_version: str
    contract_sha256: str | None
    authority_event_id: str | None
    authority_event_type: str
    authority_payload_sha256: str
    intent_sha256: str
    result_sha256: str | None
    backend_sha256: str | None
    checkpoint_sha256: str | None
    input_sha256: str | None
    output_sha256: str | None
    normalized_metrics: tuple[tuple[str, float], ...]
    verdict: Literal["PASS", "REJECT"]
    rejection_code: str | None
    authority_delta: Literal[0] = 0

    def __post_init__(self) -> None:
        if self.schema_version != RECEIPT_SCHEMA_VERSION:
            raise ValueError("unsupported activation receipt schema")
        if self.authority_delta != 0:
            raise ValueError("activation receipts cannot increase authority")
        if self.verdict == "PASS":
            if self.rejection_code is not None:
                raise ValueError("PASS receipt cannot contain a rejection code")
            required = (
                self.contract_sha256,
                self.backend_sha256,
                self.checkpoint_sha256,
                self.input_sha256,
                self.output_sha256,
            )
            if any(value is None or not _SHA256_RE.fullmatch(value) for value in required):
                raise ValueError("PASS receipt requires complete admitted digests")
        elif self.verdict == "REJECT":
            if not self.rejection_code:
                raise ValueError("REJECT receipt requires a rejection code")
        else:
            raise ValueError("unknown activation verdict")

        for key, value in self.normalized_metrics:
            if not key:
                raise ValueError("metric names cannot be empty")
            if not math.isfinite(value):
                raise ValueError("receipt metrics must be finite")

    @classmethod
    def from_evidence(
        cls,
        evidence: ActivationEvidence,
        *,
        authority_event_id: str | None = None,
    ) -> "ActivationReceipt":
        metrics: list[tuple[str, float]] = []
        primary = _finite_metric(evidence.primary_metric)
        retention = _finite_metric(evidence.retention_metric)
        if primary is not None:
            metrics.append(("primary", primary))
        if retention is not None:
            metrics.append(("retention", retention))

        verdict: Literal["PASS", "REJECT"] = (
            "PASS" if evidence.status is ActivationStatus.PASS else "REJECT"
        )
        return cls(
            schema_version=RECEIPT_SCHEMA_VERSION,
            request_id=evidence.request_id,
            model_id=evidence.model_id,
            backend_id=evidence.backend_id,
            contract_version=evidence.contract_version,
            contract_sha256=_digest_or_none(evidence.contract_sha256),
            authority_event_id=authority_event_id,
            authority_event_type=evidence.authority_event_type,
            authority_payload_sha256=evidence.authority_payload_sha256,
            intent_sha256=evidence.intent_sha256,
            result_sha256=_digest_or_none(evidence.result_sha256),
            backend_sha256=_digest_or_none(evidence.backend_sha256),
            checkpoint_sha256=_digest_or_none(evidence.checkpoint_sha256),
            input_sha256=_digest_or_none(evidence.input_sha256),
            output_sha256=_digest_or_none(evidence.output_sha256),
            normalized_metrics=tuple(sorted(metrics)),
            verdict=verdict,
            rejection_code=evidence.reject_code,
            authority_delta=0,
        )

    def canonical_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "model_id": self.model_id,
            "backend_id": self.backend_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "authority_event_id": self.authority_event_id,
            "authority_event_type": self.authority_event_type,
            "authority_payload_sha256": self.authority_payload_sha256,
            "intent_sha256": self.intent_sha256,
            "result_sha256": self.result_sha256,
            "backend_sha256": self.backend_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "normalized_metrics": dict(self.normalized_metrics),
            "verdict": self.verdict,
            "rejection_code": self.rejection_code,
            "authority_delta": self.authority_delta,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()
