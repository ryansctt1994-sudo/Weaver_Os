"""Runner failures must remain failures, including missing executables/timeouts."""

import sys

from tools.verify_all import run_step, verifier


def test_missing_program_is_failure(tmp_path):
    result = run_step("test", "missing", [str(tmp_path / "absent")], tmp_path)
    assert result["status"] == "FAIL"
    assert (tmp_path / "test--missing.log").is_file()


def test_timeout_is_failure_and_retains_output(tmp_path):
    result = run_step(
        "test",
        "timeout",
        [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(30)"],
        tmp_path,
        timeout=1,
    )
    assert result["status"] == "FAIL"
    assert "started" in (tmp_path / "test--timeout.log").read_text()


def test_nonzero_is_failure(tmp_path):
    result = run_step(
        "test", "bad", [sys.executable, "-c", "raise SystemExit(3)"], tmp_path
    )
    assert result["exit_code"] == 3
    assert result["status"] == "FAIL"


def test_verifier_status_is_derived_from_steps():
    good = {"status": "PASS", "exit_code": 0}
    bad = {"status": "FAIL", "exit_code": 7}
    assert verifier("x", [good])["status"] == "PASS"
    closed = verifier("x", [good, bad])
    assert closed["status"] == "FAIL"
    assert closed["exit_code"] == 7
