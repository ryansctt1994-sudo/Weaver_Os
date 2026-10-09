"""P0-006: aggregate verdict refusal survives producer manifest integration."""

from __future__ import annotations

import json

import pytest

from tools import verify_all


def _good_inputs():
    verifiers = [
        {
            "name": name,
            "status": "PASS",
            "exit_code": 0,
            "steps": [{"step": "run", "status": "PASS", "exit_code": 0}],
        }
        for name in verify_all.REQUIRED_VERIFIERS
    ]
    adversarial = [
        {"case_id": f"ADV-{i:03d}", "status": "PASS"} for i in range(1, 7)
    ]
    return verifiers, adversarial


def test_rerun_hashes_are_fresh_but_duplicate_verifier_must_still_refuse(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    output = root / "verification-output"
    output.mkdir()
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    (output / "unit.log").write_text("first run")
    verify_all.build_evidence_manifest(output, None)
    (output / "verification-report.json").write_text('{"old":true}')
    (output / "report.json").write_text('{"old":true}')
    (output / "unit.log").write_text("second run")

    hashes, sha = verify_all.build_evidence_manifest(output, None)
    assert hashes["verification-output/unit.log"] == verify_all.sha256_file(
        output / "unit.log"
    )
    assert not any("report.json" in name for name in hashes)
    assert "verification-output/evidence-manifest.json" not in hashes
    assert sha == verify_all.sha256_file(output / "evidence-manifest.json")
    assert json.loads((output / "evidence-manifest.json").read_text())["files"] == hashes

    verifiers, adversarial = _good_inputs()
    assert verify_all.is_valid_verdict(verifiers, adversarial, "a" * 64)
    verifiers.append(dict(verifiers[0]))
    assert not verify_all.is_valid_verdict(verifiers, adversarial, "a" * 64)


def test_collision_refusal_coexists_with_poisoned_step_rejection(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "external-output"
    output.mkdir()
    (root / "pyproject.toml").write_text("trusted")
    (output / "pyproject.toml").write_text("shadow")
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")

    with pytest.raises(ValueError, match="duplicate evidence label"):
        verify_all.build_evidence_manifest(output, None)
    assert not (output / "evidence-manifest.json").exists()

    verifiers, adversarial = _good_inputs()
    verifiers[0]["steps"][0]["exit_code"] = 1
    assert not verify_all.is_valid_verdict(verifiers, adversarial, "a" * 64)
