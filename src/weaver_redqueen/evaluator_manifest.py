from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

LEVEL_RANKS: dict[str, int] = {
    "E0": 0,
    "E1": 1,
    "E2": 2,
    "E2.5": 25,
    "E3": 3,
    "E3.5": 35,
    "E4": 4,
    "E5": 5,
    "E6": 6,
    "E7": 7,
    "E8": 8,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def level_rank(level: str) -> int:
    try:
        return LEVEL_RANKS[level]
    except KeyError as exc:
        raise ValueError(f"unknown evaluator level: {level!r}") from exc


@dataclass(frozen=True)
class EvaluatorManifest:
    evaluator_id: str
    version: str
    level: str
    criteria: Tuple[str, ...] = field(default_factory=tuple)
    mutation_invalidates: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "criteria", tuple(self.criteria))
        object.__setattr__(self, "mutation_invalidates", tuple(self.mutation_invalidates))
        level_rank(self.level)
        if not self.evaluator_id:
            raise ValueError("evaluator_id is required")
        if not self.version:
            raise ValueError("version is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator_id": self.evaluator_id,
            "version": self.version,
            "level": self.level,
            "criteria": list(self.criteria),
            "mutation_invalidates": list(self.mutation_invalidates),
            "metadata": dict(self.metadata),
        }

    def compute_hash(self) -> str:
        return sha256_json(self.to_dict())
