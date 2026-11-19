"""Artifact substitutions must be refused before loading an executable image."""

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def handoff(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "reproduction-kit" / "run.py"
    spec = importlib.util.spec_from_file_location("joint_runner", source)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "__file__", str(tmp_path / "run.py"))
    monkeypatch.setattr(
        runner.subprocess, "run", lambda *a, **kw: pytest.fail("executed unverified image")
    )
    for name in ["environment.tar", "sources.tar", "kit.json", "run.py"]:
        (tmp_path / name).write_bytes(b"synthetic fixture")
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted(tmp_path.iterdir())
        )
    )
    pin = hashlib.sha256(manifest.read_bytes()).hexdigest()
    monkeypatch.setattr(
        sys, "argv", ["run.py", "--manifest-sha256", pin, "--output", str(tmp_path / "results")]
    )
    return runner, tmp_path


@pytest.mark.parametrize("name", ["environment.tar", "sources.tar", "kit.json", "run.py"])
def test_artifact_substitution_refused_before_docker(handoff, name):
    runner, root = handoff
    (root / name).write_bytes(b"substituted bytes")
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        runner.main()
    assert not (root / "results").exists()


def test_manifest_replacement_refused_before_docker(handoff):
    runner, root = handoff
    (root / "SHA256SUMS").write_text("attacker manifest")
    with pytest.raises(ValueError, match="manifest trust pin mismatch"):
        runner.main()
