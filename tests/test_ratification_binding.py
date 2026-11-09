"""Hostile tests for machine-readable ratification claims."""

from __future__ import annotations

import copy
import json

from tools.check_ratification_binding import check_binding, check_repository

GOOD = {
    "status": "RATIFIED",
    "ratification": {
        "decision_id": "GD-0001", "ratified_at": "2026-11-07",
        "mode": "SINGLE_STEWARD", "ratified_by": ["ryansctt1994-sudo"],
    },
    "orthogonal_axes": [
        {"id": "W", "defined_levels": [{"level": "W0"}]},
        {"id": "O", "defined_levels": [{"level": "O0"}]},
    ],
}
DECISION = """# GD-0001

- **Decision ID:** GD-0001
- **Date:** 2026-11-07
- **Mode:** SINGLE_STEWARD
- **Ratified by:** Ryan Scott (`ryansctt1994-sudo`), repository owner
- **Limitation:** C-DUAL-001 remains open
"""


def _errors(mutator, decision=DECISION):
    doc = copy.deepcopy(GOOD)
    mutator(doc)
    return check_binding(doc, decision)


def test_good_decision_metadata_and_declared_axes():
    assert check_binding(GOOD, DECISION) == []


def test_missing_decision_is_not_ratification():
    assert "missing or unreadable" in " ".join(check_binding(GOOD, None))


def test_mismatched_decision_identifier():
    assert "Decision ID" in " ".join(
        _errors(lambda d: d["ratification"].update(decision_id="GD-0002"))
    )


def test_invalid_decision_id_cannot_escape_directory():
    assert "GD-NNNN" in " ".join(
        _errors(lambda d: d["ratification"].update(decision_id="../other"))
    )


def test_different_ratification_date_is_rejected():
    assert "Date" in " ".join(_errors(lambda d: d["ratification"].update(ratified_at="2026-11-08")))


def test_different_ratification_mode_is_rejected():
    assert "Mode" in " ".join(_errors(lambda d: d["ratification"].update(mode="DUAL_STEWARD")))


def test_missing_named_signatory_is_rejected():
    assert "does not name steward" in " ".join(
        _errors(lambda d: d["ratification"].update(ratified_by=["other-user"]))
    )


def test_single_steward_decision_without_limit_is_rejected():
    assert "C-DUAL-001" in " ".join(check_binding(GOOD, DECISION.replace("C-DUAL-001", "closed")))


def test_cannot_invent_witness_rung_without_policy_revision():
    assert "only W0" in " ".join(
        _errors(lambda d: d["orthogonal_axes"][0]["defined_levels"].append({"level": "W1"}))
    )


def test_cannot_invent_operational_authority_rung():
    assert "only O0" in " ".join(
        _errors(lambda d: d["orthogonal_axes"][1]["defined_levels"].append({"level": "O1"}))
    )


def test_missing_or_duplicated_axis_rejected():
    assert "unique W and O" in " ".join(_errors(lambda d: d["orthogonal_axes"][1].update(id="W")))
    assert "exactly W and O" in " ".join(_errors(lambda d: d["orthogonal_axes"].pop()))


def test_repo_check_reports_missing_decision(tmp_path):
    root = tmp_path
    (root / "governance").mkdir()
    (root / "governance/evidence_crosswalk.json").write_text(json.dumps(GOOD), encoding="utf-8")
    assert any("missing or unreadable" in error for error in check_repository(root))
