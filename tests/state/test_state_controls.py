"""WNS-S6-001: runtime-state reconstruction, digest, independent replay, negative controls."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from weaver_contracts.canonical import canonicalize
from weaver_runtime.gate import ExecutionGate, TwinVeto
from weaver_runtime.ledger import ReceiptLedger
from weaver_verifier import state as state_module
from weaver_verifier.state import (
    ANCHOR_MATCHED,
    PROJECTION,
    REDUCER_SOURCE_SHA256,
    REFUSED,
    UNANCHORED,
    state_report,
)

from tools.state_controls import LEDGER_CLOCK, LEDGER_ID, build_demo_ledger, run_controls

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def controls(tmp_path_factory):
    return {c.control: c for c in run_controls(tmp_path_factory.mktemp("controls"))}


@pytest.fixture()
def demo(tmp_path):
    return build_demo_ledger(tmp_path / "demo.db")


# --- S6-E: the nine negative controls ---------------------------------------


@pytest.mark.parametrize("control", [f"C{i}" for i in range(1, 10)])
def test_negative_control(controls, control):
    result = controls[control]
    detail = f"{result.observed_status} {result.observed_reason}"
    assert result.ok, f"{control} ({result.description}): {detail}"


def test_altered_event_is_refused(demo):
    """C1 run directly (not through the shared fixture), so a regression fails, not errors."""
    snapshot, anchor = demo
    event = json.loads(snapshot["roots"]["AUTHORITY"][1]["event"])
    event["result"]["value"] = 222
    snapshot["roots"]["AUTHORITY"][1]["event"] = canonicalize(event).decode()
    report = state_report(snapshot, anchor=anchor)
    assert report.status == REFUSED
    assert report.digest is None and report.state is None


def test_full_rewrite_is_never_reported_as_authentic(controls):
    assert controls["C4"].observed_status == UNANCHORED
    assert controls["C8"].observed_status == ANCHOR_MATCHED  # matches, yet custody unknown


# --- S6-A / S6-B: canonical schema and reconstruction --------------------------


def test_state_is_rebuilt_from_committed_events_only(demo):
    snapshot, anchor = demo
    report = state_report(snapshot, anchor=anchor)
    assert report.status == ANCHOR_MATCHED
    assert report.state["projection"] == PROJECTION
    assert sorted(report.state["executions"]) == ["p-1", "p-2", "p-3"]  # not p-denied, not p-abort
    p1 = report.state["executions"]["p-1"]
    assert p1["action"] == "SET_CONFIG" and p1["decision_id"] == "dec-p-1"
    assert p1["result_sha256"] == hashlib.sha256(b'{"applied":false,"value":1}').hexdigest()


def test_same_state_produces_identical_bytes(demo):
    snapshot, anchor = demo
    first = state_report(snapshot, anchor=anchor)
    second = state_report(json.loads(canonicalize(snapshot)), anchor=anchor)
    assert canonicalize(first.state) == canonicalize(second.state)
    assert first.digest == second.digest


def test_reconstruction_matches_the_gates_own_record(tmp_path):
    snapshot, _ = build_demo_ledger(tmp_path / "demo.db")
    with ReceiptLedger(tmp_path / "demo.db", ledger_id=LEDGER_ID) as ledger:
        gate = ExecutionGate(ledger, veto=TwinVeto(_armed()), authorize=lambda p: None)
        committed = set(gate._committed)
    assert committed == set(state_report(snapshot).state["executions"])


def test_rejections_change_the_digest_but_not_the_state(tmp_path):
    path = tmp_path / "demo.db"
    snapshot, _ = build_demo_ledger(path)
    before = state_report(snapshot)
    with ReceiptLedger(path, ledger_id=LEDGER_ID, clock=lambda: LEDGER_CLOCK) as ledger:
        ledger.reject(
            "EXECUTION_REFUSED", {"x": 1}, actor_id="g", policy_version="p", reason_code="NO"
        )
        after = state_report(ledger.snapshot())
    assert after.state == before.state
    assert after.digest != before.digest


def _commit_event(pid: str) -> dict:
    return {
        "proposal": {
            "proposal_id": pid,
            "actor_id": "a",
            "action": "DO",
            "policy_version": "v1",
            "payload": {},
        },
        "decision_id": "d1",
        "revalidation_decision_id": "d2",
        "result": {},
    }


def test_duplicate_commit_is_refused(tmp_path):
    with ReceiptLedger(tmp_path / "dup.db", ledger_id="wx", clock=lambda: LEDGER_CLOCK) as ledger:
        for _ in range(2):  # written without unique_key, as a pre-fix ledger could be
            ledger.admit(
                "EXECUTION_COMMITTED", _commit_event("p"), actor_id="g", policy_version="v"
            )
        report = state_report(ledger.snapshot())
    assert report.status == REFUSED and "committed twice" in report.reason


@pytest.mark.parametrize(
    "event_type, event",
    [
        ("STATE_TRANSITION", {"to": "EXECUTED"}),
        ("EXECUTION_COMMITTED", {"proposal": {}, "decision_id": "d", "result": {}}),
        ("EXECUTION_COMMITTED", {**_commit_event("p"), "extra": 1}),
    ],
    ids=["unsupported-event-type", "malformed-commit", "extra-field"],
)
def test_unreducible_authority_events_are_refused(tmp_path, event_type, event):
    with ReceiptLedger(tmp_path / "x.db", ledger_id="wx", clock=lambda: LEDGER_CLOCK) as ledger:
        ledger.admit(event_type, event, actor_id="g", policy_version="v")
        report = state_report(ledger.snapshot())
    assert report.status == REFUSED and "not reconstructable" in report.reason


# --- S6-C: digest binding -------------------------------------------------------


def test_digest_names_its_schema(demo):
    assert state_report(demo[0]).digest.startswith("wx-state-digest-1:")


def test_digest_binds_the_reducer_source(demo, monkeypatch):
    snapshot, _ = demo
    original = state_report(snapshot).digest
    monkeypatch.setattr(state_module, "REDUCER_SOURCE_SHA256", "0" * 64)
    assert state_report(snapshot).digest != original


def test_reducer_source_hash_is_this_files_bytes():
    source = Path(state_module.__file__).read_bytes()
    assert REDUCER_SOURCE_SHA256 == hashlib.sha256(source).hexdigest()


def test_expected_digest_mismatch_is_refused(demo):
    snapshot, anchor = demo
    good = state_report(snapshot, anchor=anchor).digest
    wrong = good[:-1] + ("0" if good[-1] != "0" else "1")
    assert state_report(snapshot, anchor=anchor, expected_digest=good).status == ANCHOR_MATCHED
    report = state_report(snapshot, anchor=anchor, expected_digest=wrong)
    assert report.status == REFUSED and "digest mismatch" in report.reason


def test_supported_reports_never_claim_authenticity_or_custody(demo):
    snapshot, anchor = demo
    for report in (state_report(snapshot), state_report(snapshot, anchor=anchor)):
        assert report.authenticity == "NOT_ESTABLISHED"
        assert report.custody == "NOT_ESTABLISHED"
        assert report.witness == "W0"


# --- S6-D: independent verification in a fresh process ------------------------


def _verify_in_fresh_process(tmp_path: Path, *args: str) -> tuple[int, dict]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.pathsep.join(
            [str(REPO / "packages" / "contracts"), str(REPO / "packages" / "verifier")]
        ),
    }
    proc = subprocess.run(
        [sys.executable, "-S", "-m", "weaver_verifier.state", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_fresh_process_reproduces_the_digest(tmp_path):
    db = tmp_path / "demo.db"
    snapshot, anchor = build_demo_ledger(db)
    in_process = state_report(snapshot, anchor=anchor).digest
    export = subprocess.run(
        [
            sys.executable, "-m", "tools.export_ledger", "--db", str(db), "--ledger-id", LEDGER_ID,
            "--snapshot-out", str(tmp_path / "s.json"), "--anchor-out", str(tmp_path / "a.json"),
        ],
        cwd=REPO,
        timeout=60,
    )
    assert export.returncode == 0
    runs = [
        _verify_in_fresh_process(tmp_path, "--snapshot", "s.json", "--anchor", "a.json")
        for _ in range(2)
    ]
    assert [code for code, _ in runs] == [0, 0]
    assert {out["digest"] for _, out in runs} == {in_process}
    assert runs[0][1]["status"] == ANCHOR_MATCHED
    assert runs[0][1]["reducer_source_sha256"] == REDUCER_SOURCE_SHA256


def test_fresh_process_has_no_runtime_code_and_refuses_tampering(tmp_path):
    snapshot, anchor = build_demo_ledger(tmp_path / "demo.db")
    snapshot["roots"]["AUTHORITY"].pop()
    (tmp_path / "s.json").write_bytes(canonicalize(snapshot))
    (tmp_path / "a.json").write_bytes(canonicalize(anchor))
    code, out = _verify_in_fresh_process(tmp_path, "--snapshot", "s.json", "--anchor", "a.json")
    assert code == 1 and out["status"] == REFUSED
    probe = subprocess.run(
        [sys.executable, "-S", "-c", "import weaver_runtime"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(REPO / "packages" / "verifier")},
        capture_output=True,
        timeout=30,
    )
    assert probe.returncode != 0  # the verifier's environment cannot reach runtime code


# --- what Step 6 must not change -----------------------------------------------


def test_e35_remains_withheld():
    proc = subprocess.run(
        [sys.executable, "verify_attestations.py", "--scope", "e35"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0


def test_published_manifest_and_kernel_deferral_are_unchanged():
    manifest = json.loads((REPO / "published_manifest.json").read_text())
    assert manifest["state_digest_status"] == "LOCAL_REDUCER_COMPUTED"
    assert manifest["state_digest_method"] == "authority-transition-reducer-v1"
    import kernel.reducer

    assert kernel.reducer.IMPLEMENTATION_STATUS == "DEFERRED_TO_BOUND_WITNESS"


def _armed():
    from tools.state_controls import _twin

    return _twin()
