"""
Admission Kernel – Minimal Gate 1 Stub.

This module provides the smallest executable admission surface needed by the
Gate 1 harness. It is intentionally conservative: complete cases with evidence
are admitted, empty cases are rejected, and claims without evidence are deferred.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AdjudicationCase:
    case_id: str
    evidence_hash: str
    submitter: str
    proposal: str


@dataclass(frozen=True)
class AdmissionDecision:
    status: str
    reason: str


def evaluate_case(case: AdjudicationCase) -> AdmissionDecision:
    if not any((case.case_id, case.evidence_hash, case.submitter, case.proposal)):
        return AdmissionDecision(status="reject", reason="empty_case")

    if not case.case_id or not case.submitter or not case.proposal:
        return AdmissionDecision(status="reject", reason="missing_required_fields")

    if not case.evidence_hash:
        return AdmissionDecision(status="defer", reason="missing_evidence")

    return AdmissionDecision(status="admit", reason="required_fields_present")
