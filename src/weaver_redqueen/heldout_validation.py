from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Tuple


def _hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HeldOutSet:
    set_id: str
    cases: Tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __init__(self, set_id: str, cases: Iterable[dict[str, Any]]):
        object.__setattr__(self, "set_id", set_id)
        object.__setattr__(self, "cases", tuple(dict(case) for case in cases))
        if not set_id:
            raise ValueError("set_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {"set_id": self.set_id, "cases": list(self.cases)}

    def compute_hash(self) -> str:
        return _hash(self.to_dict())


@dataclass(frozen=True)
class HeldOutValidationReceipt:
    receipt_id: str
    evaluator_manifest_hash: str
    heldout_set_hash: str
    validated_by: str
    passed: bool
    created_utc: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("receipt_id", "evaluator_manifest_hash", "heldout_set_hash", "validated_by", "created_utc"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "evaluator_manifest_hash": self.evaluator_manifest_hash,
            "heldout_set_hash": self.heldout_set_hash,
            "validated_by": self.validated_by,
            "passed": self.passed,
            "created_utc": self.created_utc,
            "details": dict(self.details),
        }

    def compute_hash(self) -> str:
        return _hash(self.to_dict())
