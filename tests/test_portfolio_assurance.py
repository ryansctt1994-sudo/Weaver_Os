"""Negative controls for the candidate portfolio metadata contract.

These tests intentionally do NOT test runtime execution, GitHub account security,
independent witnessing, real source provenance, or the 75 remote repositories.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools.check_portfolio_assurance import DEFAULT, check, main, read


class PortfolioAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.doc = read(DEFAULT)
        self.assertEqual(check(self.doc), [], "committed snapshot is invalid")

    def reject(self, modified, phrase):
        errors = check(modified)
        self.assertTrue(any(phrase in e for e in errors), errors)

    def test_valid_candidate_snapshot_and_cli(self):
        self.assertEqual(main([str(DEFAULT)]), 0)

    def test_valid_bounded_pinned_metric_is_not_refused(self):
        c = self.doc["claim_register"][0]
        c["reported_pass"] = 1
        c["denominator_scope"] = "one pinned source-document assertion"
        self.assertEqual(check(self.doc), [])

    def test_self_ratification_rejected(self):
        self.doc["status"] = "RATIFIED"
        self.reject(self.doc, "ratify itself")

    def test_unearned_independent_reviewer_rejected(self):
        self.doc["review"]["independent"] = True
        self.reject(self.doc, "non-independent")

    def test_inventory_dropped_entry_rejected(self):
        self.doc["inventory"]["repositories"].pop()
        self.reject(self.doc, "observed_count")

    def test_inventory_duplicate_rejected(self):
        entries = self.doc["inventory"]["repositories"]
        entries[1] = copy.deepcopy(entries[0])
        self.reject(self.doc, "duplicate repository")

    def test_inventory_false_coverage_rejected(self):
        self.doc["inventory"]["repositories"][0]["claim_coverage"] = "INDEPENDENTLY_VERIFIED"
        self.reject(self.doc, "unearned repository")

    def test_inventory_false_live_enforcement_rejected(self):
        self.doc["inventory"]["live_inventory_enforced"] = True
        self.reject(self.doc, "live inventory")

    def test_co_delete_with_recount_is_rejected(self):
        self.doc["inventory"]["repositories"].pop()
        self.doc["inventory"]["observed_count"] -= 1
        self.reject(self.doc, "frozen inventory count")

    def test_full_length_subject_rebinding_rejected(self):
        self.doc["subjects"][0]["commit"] = "0" * 40
        self.reject(self.doc, "frozen subject identity")

    def test_policy_claim_sha_rebinding_rejected(self):
        self.doc["claim_register"][0]["subject_sha"] = "0" * 40
        self.reject(self.doc, "policy source differs")

    def test_subject_partial_sha_rejected(self):
        self.doc["subjects"][0]["commit"] = "55bdfb9"
        self.reject(self.doc, "40-character")

    def test_production_promotion_rejected(self):
        self.doc["portfolio_ceiling"]["production"] = True
        self.reject(self.doc, "forbidden ceiling")

    def test_independent_witness_promotion_rejected(self):
        self.doc["portfolio_ceiling"]["witness"] = "W1"
        self.reject(self.doc, "forbidden ceiling")

    def test_gate_self_closure_rejected(self):
        self.doc["gates"][1]["status"] = "PASS"
        self.reject(self.doc, "cannot self-close")

    def test_missing_gate_rejected(self):
        self.doc["gates"].pop()
        self.reject(self.doc, "G0-G5")

    def test_claim_without_limits_rejected(self):
        self.doc["claim_register"][0]["does_not_establish"] = []
        self.reject(self.doc, "explicit limitations")

    def test_unpinned_numerical_result_rejected(self):
        c = self.doc["claim_register"][1]
        c["reported_pass"] = 507
        self.reject(self.doc, "unpinned numerical metric")

    def test_hypothesis_promoted_rejected(self):
        self.doc["claim_register"][2]["disposition"] = "SUPPORTED_BOUNDED"
        self.reject(self.doc, "research hypothesis")

    def test_single_operator_risk_missing_rejected(self):
        self.doc["risk_register"] = self.doc["risk_register"][1:]
        self.reject(self.doc, "risk entries missing")

    def test_risk_silent_closure_rejected(self):
        self.doc["risk_register"][0]["status"] = "CLOSED"
        self.reject(self.doc, "silently closed")

    def test_positive_control_absent_rejected(self):
        self.doc["falsification"]["minimum_positive_control"] = ""
        self.reject(self.doc, "positive control")

    def test_kill_criteria_removed_rejected(self):
        self.doc["falsification"]["kill_conditions"] = []
        self.reject(self.doc, "falsification")

    def test_invalidation_rule_missing_rejected(self):
        self.doc["invalidation"]["dependencies"] = []
        self.reject(self.doc, "invalidation rule")

    def test_duplicate_json_object_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.json"
            p.write_text('{"status":"HOLD","status":"PASS"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                read(p)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.json"
            p.write_text('{"status":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonfinite JSON number"):
                read(p)


if __name__ == "__main__":
    unittest.main()
