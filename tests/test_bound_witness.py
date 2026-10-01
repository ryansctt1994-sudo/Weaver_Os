"""Verify the binding between captured archive bytes and executed witness."""

import hashlib
import subprocess
from pathlib import Path

import pytest

from tools.run_verified_witness import run_verified_witness

ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"
)
EXPECTED = "5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9"


def test_replacement_after_capture_executes_verified_snapshot(tmp_path, monkeypatch):
    raw = ARCHIVE.read_bytes()
    path = tmp_path / "witness.zip"
    path.write_bytes(raw)
    original_read = Path.read_bytes
    reads = []

    def replace_after_capture(source):
        captured = original_read(source)
        reads.append(source)
        source.write_bytes(b"invalid replacement")
        return captured

    monkeypatch.setattr(Path, "read_bytes", replace_after_capture)
    receipt = run_verified_witness(path, EXPECTED)
    assert reads == [path]
    assert receipt["archive_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["returncode"] == 0
    assert "WITNESS: PASS" in receipt["stdout"]


def test_untrusted_key_never_launches_process(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("execution reached before verification")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        run_verified_witness(ARCHIVE, "0" * 64)


def test_child_failure_preserved_and_directory_cleaned(monkeypatch):
    directories = []

    def failed(command, **kwargs):
        directories.append(kwargs["cwd"])
        return subprocess.CompletedProcess(command, 7, "partial result", "failure")

    monkeypatch.setattr(subprocess, "run", failed)
    receipt = run_verified_witness(ARCHIVE, EXPECTED)
    assert receipt["returncode"] == 7
    assert receipt["stdout"] == "partial result"
    assert receipt["stderr"] == "failure"
    assert not directories[0].exists()


def test_timeout_preserved(monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 30, output=b"partial", stderr=b"timeout")

    monkeypatch.setattr(subprocess, "run", timeout)
    receipt = run_verified_witness(ARCHIVE, EXPECTED)
    assert receipt["returncode"] is None
    assert receipt["timed_out"]
    assert receipt["stdout"] == "partial"
