"""Runner failures must remain failures, including missing executables/timeouts."""

import sys

from tools.verify_all import run_check


def test_missing_program_is_failure(tmp_path):
    result = run_check("missing", [str(tmp_path / "absent")], tmp_path)
    assert result["status"] == "FAIL"
    assert (tmp_path / "missing.log").is_file()


def test_timeout_is_failure_and_retains_output(tmp_path):
    result = run_check(
        "timeout",
        [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(30)"],
        tmp_path,
        timeout=0.5,
    )
    assert result["status"] == "FAIL"
    assert "started" in (tmp_path / "timeout.log").read_text()


def test_nonzero_is_failure(tmp_path):
    result = run_check("bad", [sys.executable, "-c", "raise SystemExit(3)"], tmp_path)
    assert result["returncode"] == 3
    assert result["status"] == "FAIL"
