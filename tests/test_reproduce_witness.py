import json
import sys

import pytest

from tools import reproduce_witness as demo


def passing_result():
    return {
        "stdout": "\n".join(f"{name}...PASS" for name in demo.CHECKS) + "\nWITNESS: PASS\n",
        "returncode": 0, "timed_out": False, "archive_sha256": "expected",
    }


def test_complete_witness_passes():
    assert all(demo.assess(passing_result(), "expected").values())


@pytest.mark.parametrize("change", ["missing", "duplicate", "failure", "exit", "archive"])
def test_false_success_is_rejected(change):
    result = passing_result()
    if change == "missing":
        result["stdout"] = result["stdout"].replace("FRESH REPLAY...PASS\n", "")
    elif change == "duplicate":
        result["stdout"] += "AUTHORIZED...PASS\n"
    elif change == "failure":
        result["stdout"] += "UNEXPECTED...FAIL\n"
    elif change == "exit":
        result["returncode"] = 1
    else:
        result["archive_sha256"] = "replacement"
    assert not all(demo.assess(result, "expected").values())


def test_missing_seal_preserves_error_bundle(tmp_path, monkeypatch):
    output = tmp_path / "result"
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["demo", "--output", str(output), "--operator", "local"])
    with pytest.raises(SystemExit) as exc:
        demo.main()
    assert exc.value.code == 1
    receipt = json.loads((output / "outcome.json").read_text())
    assert receipt["status"] == "ERROR"
    assert receipt["independence"] == "NOT_ADJUDICATED"
    assert (output / "runner.stderr.txt").exists()
    assert "outcome.json" in (output / "SHA256SUMS").read_text()
