"""Portfolio review gate tests: collisions, invalid evidence, and non-promotion."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.portfolio_pr_gate import SnapshotRefusal, audit_snapshot, main, read_snapshot

SNAPSHOT = (
    Path(__file__).resolve().parents[1]
    / "docs/maintenance/P0_005_REVIEW_SNAPSHOT_2026-10-09.json"
)


@pytest.fixture
def observed():
    return read_snapshot(SNAPSHOT)


def kinds(result):
    return [item["kind"] for item in result["findings"]]


def test_real_snapshot_holds_and_identifies_exact_source_collision(observed):
    result = audit_snapshot(observed)
    assert result["result"] == "HOLD"
    assert result["assurance"] == "PROVIDER_METADATA_SNAPSHOT_ONLY"
    assert result["not_authorized"] is True
    assert result["repositories_checked"] == 3
    assert result["open_prs_reviewed"] == 6
    overlap = [item for item in result["findings"] if item["kind"] == "OVERLAPPING_OPEN_PR_PATH"]
    assert overlap == [{
        "kind": "OVERLAPPING_OPEN_PR_PATH",
        "repository": "ryansctt1994-sudo/Weaver_Os",
        "path": "tools/verify_all.py",
        "pull_requests": [80, 83],
        "detail": "overlap needs combined source and CI replay, not automatic conflict inference",
    }]


def test_absent_repo_branch_enforcement_is_never_described_as_confirmed(observed):
    result = audit_snapshot(observed)
    assert kinds(result).count("BRANCH_PROTECTION_NOT_CONFIRMED") == 3
    assert kinds(result).count("EFFECTIVE_RULESETS_UNVERIFIED") == 3
    assert kinds(result).count("DRAFT_NOT_ADMITTED") == 4


def test_only_one_repository_can_have_collisions_for_same_path(observed):
    modified = deepcopy(observed)
    modified["repositories"][1]["pull_requests"][0]["files"].append("tools/verify_all.py")
    overlap = [
        item for item in audit_snapshot(modified)["findings"]
        if item["kind"] == "OVERLAPPING_OPEN_PR_PATH"
    ]
    assert len(overlap) == 1


def test_stale_base_flagged_without_guessing_mergeability(observed):
    modified = deepcopy(observed)
    modified["repositories"][1]["pull_requests"][0]["base_sha"] = "0" * 40
    findings = audit_snapshot(modified)["findings"]
    assert any(
        f["kind"] == "BASE_SHA_STALE" and f["repository"].endswith("/Lumen")
        for f in findings
    )


def test_even_clear_snapshot_is_review_required_not_approved(observed):
    modified = deepcopy(observed)
    for repo in modified["repositories"]:
        repo["branch_protected"] = True
        repo["repository_rulesets"] = 1
        repo["organization_rulesets_checked"] = True
        for pr in repo["pull_requests"]:
            pr["draft"] = False
    modified["repositories"][0]["pull_requests"][0]["files"].remove("tools/verify_all.py")
    report = audit_snapshot(modified)
    assert report["findings"] == []
    assert report["result"] == "REVIEW_REQUIRED"
    assert report["not_authorized"] is True


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v.update({"source": "trusted-attestation"}),
        lambda v: v["repositories"][0].update({"main_sha": "not-a-sha"}),
        lambda v: v["repositories"][0]["pull_requests"][0]["files"].append("../bad"),
        lambda v: v["repositories"][0]["pull_requests"][0].update({"number": True}),
        lambda v: v["repositories"].append(deepcopy(v["repositories"][0])),
        lambda v: v["repositories"][0]["pull_requests"][0]["files"].append(
            "tools/verify_all.py"
        ),
        lambda v: v["repositories"][0]["pull_requests"][0].update({"merged": True}),
        lambda v: v["repositories"][0].update({"organization_rulesets_checked": "yes"}),
    ],
)
def test_malformed_snapshot_refused(observed, change):
    modified = deepcopy(observed)
    change(modified)
    with pytest.raises(SnapshotRefusal):
        audit_snapshot(modified)


def test_duplicate_json_member_fails_before_analysis(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text('{"schema":"a","schema":"b"}')
    with pytest.raises(SnapshotRefusal, match="duplicate"):
        read_snapshot(path)


def test_nonfinite_json_fails_before_analysis(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text('{"schema":NaN}')
    with pytest.raises(SnapshotRefusal, match="non-finite"):
        read_snapshot(path)


def test_cli_machine_gate_refuses_hold(capsys):
    assert main(["--snapshot", str(SNAPSHOT), "--fail-on-hold"]) == 1
    record = json.loads(capsys.readouterr().out)
    assert record["result"] == "HOLD"


def test_cli_advisory_mode_reports_hold_without_falsely_claiming_pass(capsys):
    assert main(["--snapshot", str(SNAPSHOT)]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["result"] == "HOLD"
    assert record["not_authorized"] is True
