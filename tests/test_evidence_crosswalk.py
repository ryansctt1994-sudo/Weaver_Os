import copy
import json

import pytest

from tools.check_evidence_crosswalk import DEFAULT_PATH, check, main


@pytest.fixture()
def doc():
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _mapping(doc, ladder_id, label):
    ladder = next(item for item in doc["source_ladders"] if item["id"] == ladder_id)
    return next(item for item in ladder["mappings"] if item["label"] == label)


def _proposed(doc):
    out = copy.deepcopy(doc)
    out["status"] = "PROPOSED"
    out["ratification"] = {"decision_id": None, "ratified_by": [], "ratified_at": None}
    return out


def _dual(doc, stewards):
    out = copy.deepcopy(doc)
    out["status"] = "RATIFIED"
    out["ratification"] = {
        "decision_id": "GD-X",
        "mode": "DUAL_STEWARD",
        "ratified_by": stewards,
        "ratified_at": "2026-11-07",
    }
    return out


def test_committed_crosswalk_is_ratified_single_steward_with_limitation(doc):
    assert check(doc) == []
    assert main([str(DEFAULT_PATH)]) == 0
    ratification = doc["ratification"]
    assert doc["status"] == "RATIFIED"
    assert ratification["decision_id"] == "GD-0001"
    assert ratification["mode"] == "SINGLE_STEWARD"
    assert ratification["ratified_by"] == ["ryansctt1994-sudo"]
    assert "C-DUAL-001" in ratification["limitation"]


def test_single_independent_replay_does_not_reach_r4(doc):
    assert _mapping(doc, "lumen_e", "E4")["maps_to"] == "R3"
    assert _mapping(doc, "weaver_e", "E4")["maps_to"] == "R3"


def test_proposed_baseline_is_valid(doc):
    assert check(_proposed(doc)) == []


def test_ratified_without_decision_is_rejected(doc):
    bad = copy.deepcopy(doc)
    bad["ratification"]["decision_id"] = None
    assert any("decision_id" in e for e in check(bad))


def test_ratified_without_mode_is_rejected(doc):
    bad = copy.deepcopy(doc)
    del bad["ratification"]["mode"]
    assert any("mode" in e for e in check(bad))


def test_single_steward_without_limitation_is_rejected(doc):
    bad = copy.deepcopy(doc)
    del bad["ratification"]["limitation"]
    assert any("C-DUAL-001" in e for e in check(bad))


def test_single_steward_limitation_must_name_blocker(doc):
    bad = copy.deepcopy(doc)
    bad["ratification"]["limitation"] = "approved alone"
    assert any("C-DUAL-001" in e for e in check(bad))


def test_single_steward_with_two_names_is_rejected(doc):
    bad = copy.deepcopy(doc)
    bad["ratification"]["ratified_by"] = ["steward-a", "steward-b"]
    assert any("exactly one steward" in e for e in check(bad))


def test_dual_steward_with_one_distinct_name_is_rejected(doc):
    assert any("distinct stewards" in e for e in check(_dual(doc, ["a", "a"])))


def test_dual_steward_with_two_stewards_passes(doc):
    assert check(_dual(doc, ["steward-a", "steward-b"])) == []


def test_proposed_with_ratification_data_is_rejected(doc):
    bad = _proposed(doc)
    bad["ratification"]["ratified_by"] = ["steward-a"]
    assert any("must not carry ratification" in e for e in check(bad))


def test_non_monotonic_mapping_is_rejected(doc):
    bad = copy.deepcopy(doc)
    _mapping(bad, "lumen_e", "E3")["maps_to"] = "R1"
    assert any("monotonic" in e for e in check(bad))


def test_mapping_to_production_is_rejected(doc):
    bad = copy.deepcopy(doc)
    _mapping(bad, "lumen_e", "E5")["maps_to"] = "R6"
    assert any("production" in e for e in check(bad))


def test_floor_without_condition_is_rejected(doc):
    bad = copy.deepcopy(doc)
    del _mapping(bad, "lumen_e", "E4")["condition_for_higher"]
    assert any("condition_for_higher" in e for e in check(bad))


def test_unknown_target_level_is_rejected(doc):
    bad = copy.deepcopy(doc)
    _mapping(bad, "lumen_e", "E2")["maps_to"] = "R2.5"
    assert any("not an R level" in e for e in check(bad))


def test_status_flag_must_not_claim_equivalence(doc):
    bad = copy.deepcopy(doc)
    _mapping(bad, "triad_labels", "FAILED")["equivalence"] = "exact"
    assert any("STATUS_FLAG" in e for e in check(bad))


def test_reordered_target_ladder_is_rejected(doc):
    bad = copy.deepcopy(doc)
    levels = bad["target_ladder"]["levels"]
    levels[3], levels[4] = levels[4], levels[3]
    assert any("exactly" in e for e in check(bad))


def test_duplicate_label_is_rejected(doc):
    bad = copy.deepcopy(doc)
    ladder = bad["source_ladders"][0]
    ladder["mappings"].append(copy.deepcopy(ladder["mappings"][0]))
    assert any("duplicate label" in e for e in check(bad))
