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


def test_committed_crosswalk_is_valid_and_only_proposed(doc):
    assert check(doc) == []
    assert doc["status"] == "PROPOSED"
    assert main([str(DEFAULT_PATH)]) == 0


def test_single_independent_replay_does_not_reach_r4(doc):
    assert _mapping(doc, "lumen_e", "E4")["maps_to"] == "R3"
    assert _mapping(doc, "weaver_e", "E4")["maps_to"] == "R3"


def test_ratified_without_decision_is_rejected(doc):
    bad = copy.deepcopy(doc)
    bad["status"] = "RATIFIED"
    assert any("decision_id" in e for e in check(bad))


def test_ratified_by_one_steward_is_rejected(doc):
    bad = copy.deepcopy(doc)
    bad["status"] = "RATIFIED"
    bad["ratification"] = {
        "decision_id": "GD-1",
        "ratified_by": ["steward-a", "steward-a"],
        "ratified_at": "2026-11-07",
    }
    assert any("distinct stewards" in e for e in check(bad))


def test_ratified_with_two_stewards_passes(doc):
    good = copy.deepcopy(doc)
    good["status"] = "RATIFIED"
    good["ratification"] = {
        "decision_id": "GD-1",
        "ratified_by": ["steward-a", "steward-b"],
        "ratified_at": "2026-11-07",
    }
    assert check(good) == []


def test_proposed_with_ratification_data_is_rejected(doc):
    bad = copy.deepcopy(doc)
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
