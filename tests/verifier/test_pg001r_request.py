"""PG-001R requests are read strictly before the unchanged gate evaluates them.

``weaver_verifier.pg001r`` stays byte-identical to its Lumen-Nexus source (see
``test_pg001r_identity.py``), including a ``main()`` that reads requests with plain
``json.loads``. That reader keeps the last of a duplicated key, so a request can show a
reviewer an open contradiction (blocker B03) and be evaluated without it. It also lets a
deeply nested body escape as a traceback, which shares exit code 1 with "blocked".

``weaver_verifier.pg001r_request`` is the supported entry point: strict reading, then the
same contract and evaluator. Exit codes: 0 eligible, 1 blocked, 2 input rejected.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from weaver_contracts.pg001r import ContractError
from weaver_verifier.pg001r_request import MAX_REQUEST_BYTES, load_request, main

ROOT = Path(__file__).resolve().parents[2]
# Run the module from this tree, not from whatever copy happens to be installed.
ENV = {**os.environ, "PYTHONPATH": os.pathsep.join(
    str(ROOT / "packages" / name) for name in ("contracts", "verifier")
)}

BASE = {
    "artifact_id": "A-1",
    "current_evidence_level": "R1",
    "verified_evidence_level": "R2",
    "requested_evidence_level": "R2",
    "requested_authority": "NONE",
    "required_evidence": ["e1"],
    "verified_evidence": ["e1"],
    "recorded_evidence": ["e1"],
    "open_contradictions": [],
    "recovery_dependencies_required": [],
    "recovery_dependencies_present": [],
    "self_issued_receipt_only": True,
    "independent_reproduction_receipts": 0,
    "external_publication_claimed_as_evidence": False,
    "external_publication_receipt_bound": False,
    "governance_bundle_id": None,
    "gate_decision_id": None,
    "human_authority_id": None,
    "clinical_scope": False,
    "clinical_safety_level": "NOT_APPLICABLE",
}


def _hidden_contradiction() -> bytes:
    # Read top-down, this request lists an open contradiction. A last-key-wins reader
    # evaluates the trailing empty list instead.
    shown = json.dumps(dict(BASE, open_contradictions=["C-1"]))
    return (shown[:-1] + ', "open_contradictions": []}').encode()


def test_a_valid_request_is_evaluated():
    request = load_request(json.dumps(BASE).encode())
    assert request.artifact_id == "A-1"


def test_a_duplicated_key_is_refused_not_resolved():
    with pytest.raises(ContractError, match="duplicate"):
        load_request(_hidden_contradiction())


def test_the_moved_entry_point_still_has_the_ambiguity_this_one_closes(tmp_path):
    # Documents why the strict entry point exists: the byte-identical moved module's own
    # main() evaluates the hidden-contradiction request as eligible.
    path = tmp_path / "request.json"
    path.write_bytes(_hidden_contradiction())
    moved = subprocess.run(
        [sys.executable, "-m", "weaver_verifier.pg001r", str(path)],
        cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=30,
    )
    assert moved.returncode == 0 and json.loads(moved.stdout)["allowed"] is True
    assert main([str(path)]) == 2


@pytest.mark.parametrize(
    "body",
    [
        b"[" * 20000 + b"]" * 20000,  # nesting the recursive parser cannot survive
        json.dumps(BASE).replace('"independent_reproduction_receipts": 0',
                                 '"independent_reproduction_receipts": NaN').encode(),
        json.dumps(BASE).replace('"independent_reproduction_receipts": 0',
                                 '"independent_reproduction_receipts": 1.0').encode(),
        b"\xef\xbb\xbf" + json.dumps(BASE).encode(),  # byte-order mark
        b"[]",  # not an object
    ],
    ids=["deep", "nan", "float", "bom", "array"],
)
def test_malformed_requests_are_rejected_with_exit_code_2(tmp_path, body, capsys):
    path = tmp_path / "request.json"
    path.write_bytes(body)
    assert main([str(path)]) == 2
    assert "PG-001R input rejected" in capsys.readouterr().err


def test_an_oversized_request_is_rejected_before_parsing(tmp_path):
    path = tmp_path / "request.json"
    path.write_bytes(b" " * (MAX_REQUEST_BYTES + 1))
    assert main([str(path)]) == 2


def test_exit_codes_separate_eligible_blocked_and_rejected(tmp_path, capsys):
    eligible = tmp_path / "eligible.json"
    eligible.write_text(json.dumps(BASE))
    assert main([str(eligible)]) == 0
    assert json.loads(capsys.readouterr().out)["allowed"] is True

    blocked = tmp_path / "blocked.json"
    blocked.write_text(json.dumps(dict(BASE, open_contradictions=["C-1"])))
    assert main([str(blocked)]) == 1
    decision = json.loads(capsys.readouterr().out)
    assert decision["allowed"] is False
    assert [b["code"] for b in decision["blockers"]] == ["B03"]

    assert main([str(tmp_path / "missing.json")]) == 2
    assert main([]) == 2


def test_runs_as_a_module(tmp_path):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(BASE))
    done = subprocess.run(
        [sys.executable, "-m", "weaver_verifier.pg001r_request", str(path)],
        cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=30,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["allowed"] is True
