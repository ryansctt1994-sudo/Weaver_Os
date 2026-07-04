from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScoringReceipt:
    receipt_id: str
    evaluator_manifest_hash: str
    subject_id: str
    score: float
    created_utc: str
    payload_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        receipt_id: str,
        evaluator_manifest_hash: str,
        subject_id: str,
        score: float,
        created_utc: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ScoringReceipt":
        if not 0 <= score <= 1:
            raise ValueError("score must be between 0 and 1")
        payload_hash = _hash(payload or {})
        return cls(receipt_id, evaluator_manifest_hash, subject_id, score, created_utc, payload_hash, metadata or {})

    def is_valid_after_evaluator_change(self, new_evaluator_manifest_hash: str) -> bool:
        return self.evaluator_manifest_hash == new_evaluator_manifest_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "evaluator_manifest_hash": self.evaluator_manifest_hash,
            "subject_id": self.subject_id,
            "score": self.score,
            "created_utc": self.created_utc,
            "payload_hash": self.payload_hash,
            "metadata": dict(self.metadata),
        }

    def compute_hash(self) -> str:
        return _hash(self.to_dict())
