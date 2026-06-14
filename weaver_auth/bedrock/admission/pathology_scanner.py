"""
Pathology Scanner – Minimal Gate 1 Observer Stub

GP flags are observational only. The scanner records possible governance
pathologies without blocking or mutating admission decisions.
"""
from typing import List
from .admission_kernel import AdjudicationCase


KNOWN_FLAGS = ("GP-001", "GP-002", "GP-003", "GP-004", "GP-005", "GP-006")


def scan_case(case: AdjudicationCase) -> List[str]:
    flags: List[str] = []

    proposal = case.proposal.lower() if case.proposal else ""

    if not case.evidence_hash:
        flags.append("GP-001")
    if "authority" in proposal and "evidence" not in proposal:
        flags.append("GP-002")
    if "trust me" in proposal:
        flags.append("GP-003")

    return [flag for flag in flags if flag in KNOWN_FLAGS]
