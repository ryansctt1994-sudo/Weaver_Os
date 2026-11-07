from __future__ import annotations

import unittest
from dataclasses import replace

from weaver_contracts.pg001r import (
    AuthorityLevel,
    EvidenceLevel,
    PromotionRequest,
)
from weaver_verifier.pg001r import evaluate


def request(**overrides: object) -> PromotionRequest:
    base = PromotionRequest(
        artifact_id="PG-001R-TEST",
        current_evidence_level=EvidenceLevel.R0,
        verified_evidence_level=EvidenceLevel.R1,
        requested_evidence_level=EvidenceLevel.R1,
        requested_authority=AuthorityLevel.NONE,
        required_evidence=("spec",),
        verified_evidence=("spec",),
        recorded_evidence=("spec",),
        open_contradictions=(),
        recovery_dependencies_required=(),
        recovery_dependencies_present=(),
        self_issued_receipt_only=True,
        independent_reproduction_receipts=0,
        external_publication_claimed_as_evidence=False,
        external_publication_receipt_bound=False,
        governance_bundle_id=None,
        gate_decision_id=None,
        human_authority_id=None,
        clinical_scope=False,
        clinical_safety_level="NOT_APPLICABLE",
    )
    return replace(base, **overrides)


def blocker_codes(candidate: PromotionRequest) -> set[str]:
    return {blocker.code for blocker in evaluate(candidate).blockers}


class PG001RConformanceTests(unittest.TestCase):
    def test_01_noop_none_authority_allowed(self) -> None:
        candidate = request(
            current_evidence_level=EvidenceLevel.R1,
            verified_evidence_level=EvidenceLevel.R1,
            requested_evidence_level=EvidenceLevel.R1,
        )
        decision = evaluate(candidate)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.eligible_authority, "NONE")

    def test_02_r1_spec_promotion_allowed(self) -> None:
        decision = evaluate(request())
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.effective_evidence_level, "R1")

    def test_03_evidence_ceiling_blocks_requested_level(self) -> None:
        candidate = request(requested_evidence_level=EvidenceLevel.R2)
        self.assertIn("B01", blocker_codes(candidate))

    def test_04_required_evidence_subset_violation_blocks(self) -> None:
        candidate = request(required_evidence=("spec", "tests"))
        self.assertIn("I01", blocker_codes(candidate))

    def test_05_verified_evidence_subset_violation_blocks(self) -> None:
        candidate = request(
            verified_evidence=("spec", "tests"),
            recorded_evidence=("spec",),
        )
        self.assertIn("I02", blocker_codes(candidate))

    def test_06_r4_requires_two_independent_receipts(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R4,
            requested_evidence_level=EvidenceLevel.R4,
            self_issued_receipt_only=False,
            independent_reproduction_receipts=1,
        )
        self.assertIn("B02", blocker_codes(candidate))

    def test_07_r4_rejects_self_issued_only(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R4,
            requested_evidence_level=EvidenceLevel.R4,
            self_issued_receipt_only=True,
            independent_reproduction_receipts=2,
        )
        self.assertIn("B02", blocker_codes(candidate))

    def test_08_r4_with_two_independent_receipts_allowed(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R4,
            requested_evidence_level=EvidenceLevel.R4,
            self_issued_receipt_only=False,
            independent_reproduction_receipts=2,
        )
        self.assertTrue(evaluate(candidate).allowed)

    def test_09_open_contradiction_blocks(self) -> None:
        candidate = request(open_contradictions=("C-TEST-001",))
        self.assertIn("B03", blocker_codes(candidate))

    def test_10_missing_recovery_dependency_blocks(self) -> None:
        candidate = request(
            recovery_dependencies_required=("restore-script", "backup-key"),
            recovery_dependencies_present=("restore-script",),
        )
        self.assertIn("B04", blocker_codes(candidate))

    def test_11_complete_recovery_dependencies_allowed(self) -> None:
        candidate = request(
            recovery_dependencies_required=("restore-script", "backup-key"),
            recovery_dependencies_present=("backup-key", "restore-script"),
        )
        self.assertTrue(evaluate(candidate).allowed)

    def test_12_external_publication_inflation_blocks(self) -> None:
        candidate = request(
            external_publication_claimed_as_evidence=True,
            external_publication_receipt_bound=False,
        )
        self.assertIn("B05", blocker_codes(candidate))

    def test_13_bound_external_publication_does_not_block(self) -> None:
        candidate = request(
            external_publication_claimed_as_evidence=True,
            external_publication_receipt_bound=True,
        )
        self.assertTrue(evaluate(candidate).allowed)

    def test_14_authority_requires_governance_bundle(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R2,
            requested_evidence_level=EvidenceLevel.R2,
            requested_authority=AuthorityLevel.INTERNAL,
            gate_decision_id="GATE-1",
            human_authority_id="HUMAN-1",
        )
        self.assertIn("B06", blocker_codes(candidate))

    def test_15_authority_requires_gate_decision(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R2,
            requested_evidence_level=EvidenceLevel.R2,
            requested_authority=AuthorityLevel.INTERNAL,
            governance_bundle_id="GOV-1",
            human_authority_id="HUMAN-1",
        )
        self.assertIn("B06", blocker_codes(candidate))

    def test_16_authority_evidence_floor_blocks(self) -> None:
        candidate = request(
            requested_authority=AuthorityLevel.INTERNAL,
            governance_bundle_id="GOV-1",
            gate_decision_id="GATE-1",
            human_authority_id="HUMAN-1",
        )
        self.assertIn("B06", blocker_codes(candidate))

    def test_17_internal_authority_allowed_at_r2(self) -> None:
        candidate = request(
            verified_evidence_level=EvidenceLevel.R2,
            requested_evidence_level=EvidenceLevel.R2,
            requested_authority=AuthorityLevel.INTERNAL,
            governance_bundle_id="GOV-1",
            gate_decision_id="GATE-1",
            human_authority_id="HUMAN-1",
        )
        decision = evaluate(candidate)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.eligible_authority, "INTERNAL")

    def test_18_clinical_c0_blocks_promotion(self) -> None:
        candidate = request(clinical_scope=True, clinical_safety_level="C0")
        self.assertIn("B07", blocker_codes(candidate))

    def test_19_clinical_c1_non_authority_promotion_allowed(self) -> None:
        candidate = request(clinical_scope=True, clinical_safety_level="C1")
        self.assertTrue(evaluate(candidate).allowed)


if __name__ == "__main__":
    unittest.main()
