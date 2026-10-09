"""A rerun must bind final evidence bytes, never its own previous output."""
import hashlib
import json

import pytest

from tools import verify_all


@pytest.mark.parametrize("inside_root", [True, False])
def test_rerun_manifest_matches_final_bytes(tmp_path, monkeypatch, inside_root):
    root = tmp_path / "repo"
    root.mkdir()
    output = (root if inside_root else tmp_path) / "evidence"
    output.mkdir()
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    (output / "check.log").write_text("first run\n")
    verify_all.build_evidence_manifest(output, None)
    for name in ("verification-report.json", "report.json"):
        (output / name).write_text('{"run": 1}\n')
    (output / "check.log").write_text("second run\n")
    hashes, digest = verify_all.build_evidence_manifest(output, None)
    # Main writes these after constructing the evidence manifest.
    for name in ("verification-report.json", "report.json"):
        (output / name).write_text('{"run": 2}\n')
    mismatches = []
    for label, expected in hashes.items():
        path = root / label
        if not path.is_file():
            path = output / label
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            mismatches.append(label)
    assert mismatches == []
    assert hashlib.sha256((output / "evidence-manifest.json").read_bytes()).hexdigest() == digest
    assert json.loads((output / "evidence-manifest.json").read_text())["files"] == hashes


def test_manifest_preserves_logs_and_wheel(tmp_path, monkeypatch):
    monkeypatch.setattr(verify_all, "ROOT", tmp_path)
    monkeypatch.setattr(verify_all, "LOCKFILE", tmp_path / "requirements-verification.lock")
    output = tmp_path / "output"
    output.mkdir()
    (output / "install.log").write_text("dependency installation evidence")
    (output / "adversarial-results.json").write_text('{"results": []}')
    wheel = tmp_path / "fixture.whl"
    wheel.write_bytes(b"synthetic fixture, not a built distribution")
    hashes, _ = verify_all.build_evidence_manifest(output, wheel)
    assert set(hashes) == {"output/install.log", "output/adversarial-results.json", "fixture.whl"}
