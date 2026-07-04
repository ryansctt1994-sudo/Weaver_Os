from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def _hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Epoch:
    epoch_id: str
    evaluator_manifest_hash: str
    heldout_set_hash: str
    opened_utc: str
    closed_utc: str | None = None

    def __post_init__(self) -> None:
        for name in ("epoch_id", "evaluator_manifest_hash", "heldout_set_hash", "opened_utc"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if len(self.evaluator_manifest_hash) != 64 or len(self.heldout_set_hash) != 64:
            raise ValueError("manifest and held-out hashes must be SHA-256 hex strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch_id": self.epoch_id,
            "evaluator_manifest_hash": self.evaluator_manifest_hash,
            "heldout_set_hash": self.heldout_set_hash,
            "opened_utc": self.opened_utc,
            "closed_utc": self.closed_utc,
        }

    def compute_hash(self) -> str:
        return _hash(self.to_dict())
