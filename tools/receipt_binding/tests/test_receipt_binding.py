"""Tests for RECEIPT_BINDING_GATE_v1.

P12 self-application: this suite proves the gate's rejection paths fire, not
only its acceptance path. A binding gate that only ever VERIFIES is unverified.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from receipt_binding import Status, bind_receipt  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")
TREE = os.path.join(FIX, "artifact_tree")

GREEN = [sys.executable, "-c", "import sys; sys.exit(0)"]
RED = [sys.executable, "-c", "import sys; sys.exit(1)"]


def load(name: str) -> dict:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


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


FORGED = os.path.abspath(os.path.join(FIX, "forged_receipt.json"))


def neg_good() -> list[str]:
    return make_neg_control(FORGED, os.path.abspath(TREE))


def test_verified_when_all_gates_pass():
    result = bind_receipt(load("valid_receipt.json"), TREE, GREEN, neg_good())
    assert result.status is Status.VERIFIED
    assert result.verified
    assert bool(result) is True


def test_hash_mismatch_rejected():
    result = bind_receipt(load("forged_receipt.json"), TREE, GREEN, neg_good())
    assert result.status is Status.REJECTED_HASH_MISMATCH
    assert "beta.txt" in result.hash_diffs
    assert not result.verified


def test_missing_file_is_hash_mismatch():
    receipt = load("valid_receipt.json")
    receipt["hashes"]["does_not_exist.txt"] = "ab" * 32
    result = bind_receipt(receipt, TREE, GREEN, neg_good())
    assert result.status is Status.REJECTED_HASH_MISMATCH
    assert result.hash_diffs["does_not_exist.txt"]["actual"] is None


def test_replay_failure_rejected():
    result = bind_receipt(load("valid_receipt.json"), TREE, RED, neg_good())
    assert result.status is Status.REJECTED_REPLAY_FAILED
    assert result.replay_returncode == 1


def test_negative_control_failure_rejected():
    result = bind_receipt(load("valid_receipt.json"), TREE, GREEN, GREEN)
    assert result.status is Status.REJECTED_NEGATIVE_CONTROL_FAILED
    assert result.negative_control_returncode == 0
    assert not result.verified


def test_negative_control_actually_catches_real_forgery():
    proc = subprocess.run(neg_good(), cwd=TREE, capture_output=True, text=True)
    assert proc.returncode != 0, "negative control failed to reject the known forgery"


def test_error_on_no_hashes():
    result = bind_receipt({"status": "DRAFT"}, TREE, GREEN, neg_good())
    assert result.status is Status.ERROR


def test_error_on_bad_artifact_root():
    result = bind_receipt(load("valid_receipt.json"), "/no/such/dir", GREEN, neg_good())
    assert result.status is Status.ERROR


def test_gate_order_hash_before_replay():
    result = bind_receipt(load("forged_receipt.json"), TREE, RED, neg_good())
    assert result.status is Status.REJECTED_HASH_MISMATCH
