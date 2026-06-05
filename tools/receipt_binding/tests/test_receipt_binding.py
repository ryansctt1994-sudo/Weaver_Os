"""Tests for RECEIPT_BINDING_GATE_v1.

P12 self-application: this suite proves the gate's rejection paths fire, not
only its acceptance path. A binding gate that only ever VERIFIES is unverified.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from receipt_binding import Status, bind_receipt  # noqa: E402

GREEN = [sys.executable, "-c", "import sys; sys.exit(0)"]
RED = [sys.executable, "-c", "import sys; sys.exit(1)"]


def make_tree(tmp_path: Path) -> tuple[str, dict, dict, str]:
    tree = tmp_path / "artifact_tree"
    tree.mkdir()
    (tree / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    (tree / "beta.txt").write_text("beta\n", encoding="utf-8")

    valid = {
        "status": "DRAFT",
        "hashes": {
            "alpha.txt": hashlib.sha256(b"alpha\n").hexdigest(),
            "beta.txt": hashlib.sha256(b"beta\n").hexdigest(),
        },
    }
    forged = {
        "status": "VERIFIED",
        "hashes": {
            "alpha.txt": hashlib.sha256(b"alpha\n").hexdigest(),
            "beta.txt": "0" * 64,
        },
    }
    forged_path = tmp_path / "forged_receipt.json"
    forged_path.write_text(json.dumps(forged), encoding="utf-8")
    return str(tree), valid, forged, str(forged_path)


def make_neg_control(forged_path: str, tree: str) -> list[str]:
    code = (
        "import json,hashlib,os,sys;"
        f"r=json.load(open({forged_path!r}));"
        "bad=0\n"
        "for rel,h in r['hashes'].items():\n"
        f"    p=os.path.join({tree!r},rel)\n"
        "    a=hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.isfile(p) else None\n"
        "    if a!=h: bad+=1\n"
        "sys.exit(1 if bad else 0)"
    )
    return [sys.executable, "-c", code]


def test_verified_when_all_gates_pass(tmp_path):
    tree, valid, _forged, forged_path = make_tree(tmp_path)
    result = bind_receipt(valid, tree, GREEN, make_neg_control(forged_path, tree))
    assert result.status is Status.VERIFIED
    assert result.verified
    assert bool(result) is True


def test_hash_mismatch_rejected(tmp_path):
    tree, _valid, forged, forged_path = make_tree(tmp_path)
    result = bind_receipt(forged, tree, GREEN, make_neg_control(forged_path, tree))
    assert result.status is Status.REJECTED_HASH_MISMATCH
    assert "beta.txt" in result.hash_diffs
    assert not result.verified


def test_missing_file_is_hash_mismatch(tmp_path):
    tree, valid, _forged, forged_path = make_tree(tmp_path)
    valid["hashes"]["does_not_exist.txt"] = "ab" * 32
    result = bind_receipt(valid, tree, GREEN, make_neg_control(forged_path, tree))
    assert result.status is Status.REJECTED_HASH_MISMATCH
    assert result.hash_diffs["does_not_exist.txt"]["actual"] is None


def test_replay_failure_rejected(tmp_path):
    tree, valid, _forged, forged_path = make_tree(tmp_path)
    result = bind_receipt(valid, tree, RED, make_neg_control(forged_path, tree))
    assert result.status is Status.REJECTED_REPLAY_FAILED
    assert result.replay_returncode == 1


def test_negative_control_failure_rejected(tmp_path):
    tree, valid, _forged, _forged_path = make_tree(tmp_path)
    result = bind_receipt(valid, tree, GREEN, GREEN)
    assert result.status is Status.REJECTED_NEGATIVE_CONTROL_FAILED
    assert result.negative_control_returncode == 0
    assert not result.verified


def test_negative_control_actually_catches_real_forgery(tmp_path):
    tree, _valid, _forged, forged_path = make_tree(tmp_path)
    proc = subprocess.run(make_neg_control(forged_path, tree), cwd=tree, capture_output=True, text=True)
    assert proc.returncode != 0, "negative control failed to reject the known forgery"


def test_error_on_no_hashes(tmp_path):
    tree, _valid, _forged, forged_path = make_tree(tmp_path)
    result = bind_receipt({"status": "DRAFT"}, tree, GREEN, make_neg_control(forged_path, tree))
    assert result.status is Status.ERROR


def test_error_on_bad_artifact_root(tmp_path):
    _tree, valid, _forged, forged_path = make_tree(tmp_path)
    result = bind_receipt(valid, "/no/such/dir", GREEN, make_neg_control(forged_path, "/no/such/dir"))
    assert result.status is Status.ERROR


def test_gate_order_hash_before_replay(tmp_path):
    tree, _valid, forged, forged_path = make_tree(tmp_path)
    result = bind_receipt(forged, tree, RED, make_neg_control(forged_path, tree))
    assert result.status is Status.REJECTED_HASH_MISMATCH
