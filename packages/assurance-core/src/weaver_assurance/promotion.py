"""Evidence promotion rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class EvidenceLevel(IntEnum):
    E0 = 0
    E1 = 1
    E2 = 2
    E3 = 3
    E4 = 4
    E5 = 5
    E6 = 6


REQUIREMENTS: dict[EvidenceLevel, set[str]] = {
    EvidenceLevel.E1: {"claim", "scope", "non_claims"},
    EvidenceLevel.E2: {"command", "exit_code", "tests", "failure_path", "local_receipt"},
    EvidenceLevel.E3: {"locked_environment", "artifact_hashes", "replay_command", "replay_receipt"},
    EvidenceLevel.E4: {"distinct_witness", "witness_transcript", "witness_receipt"},
    EvidenceLevel.E5: {"qualified_reviewer", "domain_validation", "limitations"},
    EvidenceLevel.E6: {"deployment_controls", "monitoring", "rollback", "incident_response"},
}


@dataclass(frozen=True)
class PromotionDecision:
    granted: bool
    requested: EvidenceLevel
    missing: tuple[str, ...]
    reason: str


def evaluate_promotion(requested: EvidenceLevel, available: Iterable[str]) -> PromotionDecision:
    supplied = set(available)
    required: set[str] = set()
    for level, items in REQUIREMENTS.items():
        if level <= requested:
            required.update(items)
    missing = tuple(sorted(required - supplied))
    if missing:
        return PromotionDecision(False, requested, missing, "PROMOTION_BLOCKED_MISSING_EVIDENCE")
    return PromotionDecision(True, requested, (), "PROMOTION_GRANTED_WITH_DECLARED_EVIDENCE")

