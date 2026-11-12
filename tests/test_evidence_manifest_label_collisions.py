"""P0-003: manifest keys must not identify two distinct source paths."""

from __future__ import annotations

import json

import pytest

from tools import verify_all


def test_outside_output_cannot_shadow_repository_source_label(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "external-output"
    output.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='trusted'\n")
    (output / "pyproject.toml").write_text("[project]\nname='shadow'\n")
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")

    with pytest.raises(ValueError, match="duplicate evidence label"):
        verify_all.build_evidence_manifest(output, None)
    assert not (output / "evidence-manifest.json").exists()


def test_outside_output_noncolliding_labels_still_work(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "external-output"
    output.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='trusted'\n")
    (output / "verification.log").write_text("verified log contents\n")
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")

    hashes, _ = verify_all.build_evidence_manifest(output, None)
    manifest = json.loads((output / "evidence-manifest.json").read_text())
    assert set(hashes) == {"pyproject.toml", "verification.log"}
    assert manifest["files"] == hashes


def test_duplicate_candidate_for_same_physical_file_is_not_collision(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    output = root / "out"
    output.mkdir()
    source = root / "pyproject.toml"
    source.write_text("[project]\nname='trusted'\n")
    monkeypatch.setattr(verify_all, "ROOT", root)
    monkeypatch.setattr(verify_all, "LOCKFILE", root / "requirements-verification.lock")

    # Simulate the runner considering the same source as an explicit input and wheel.
    hashes, _ = verify_all.build_evidence_manifest(output, source)
    assert "pyproject.toml" in hashes
