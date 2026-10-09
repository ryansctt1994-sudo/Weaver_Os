"""Synthetic and adversarial evidence-bundle checks for the standalone verifier."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from tools.verify_evidence_bundle import BundleRefusal, verify_bundle

ROOT = Path(__file__).resolve().parents[1]
VERIFIERS = (
    "unit_and_integration",
    "bound_witness",
    "mutation_suite",
    "adversarial_corpus",
    "installed_wheel",
    "formal_tlc",
    "static_analysis_strict",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def fixture_bundle(tmp_path: Path, outside: bool = False) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "outside" if outside else root / "verification-output"
    output.mkdir()
    (root / "schemas").mkdir()
    shutil.copy2(
        ROOT / "schemas" / "verification_run.schema.json",
        root / "schemas" / "verification_run.schema.json",
    )
    (root / "requirements-verification.lock").write_text("synthetic pinned fixture\n")
    (root / "pyproject.toml").write_text("[project]\nname='test'\n")
    wheel = root / "dist" / "local_fixture.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"synthetic wheel bytes, not an executable distribution")
    files = {
        "schemas/verification_run.schema.json": sha256(
            (root / "schemas" / "verification_run.schema.json").read_bytes()
        ),
        "requirements-verification.lock": sha256(
            (root / "requirements-verification.lock").read_bytes()
        ),
        "pyproject.toml": sha256((root / "pyproject.toml").read_bytes()),
        "dist/local_fixture.whl": sha256(wheel.read_bytes()),
    }

    verifiers = []
    for name in VERIFIERS:
        log = f"{name}--run.log"
        log_path = output / log
        log_path.write_text(f"synthetic {name} PASS\n")
        label = log if outside else f"verification-output/{log}"
        files[label] = sha256(log_path.read_bytes())
        verifiers.append(
            {
                "name": name,
                "status": "PASS",
                "exit_code": 0,
                "steps": [
                    {
                        "step": "run",
                        "command": ["synthetic-verifier", name],
                        "exit_code": 0,
                        "status": "PASS",
                        "log": log,
                        "log_sha256": files[label],
                    }
                ],
            }
        )

    cases = []
    for i in range(1, 7):
        fixture = f"test-{i}.jsonl"
        path = root / "tests" / "fixtures" / "verification" / fixture
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'{{"case":{i}}}\n')
        digest = sha256(path.read_bytes())
        files[f"tests/fixtures/verification/{fixture}"] = digest
        cases.append(
            {
                "case_id": f"ADV-{i:03d}",
                "case_name": f"case {i}",
                "expected_verdict": "REJECT",
                "observed_verdict": "REJECT",
                "status": "PASS",
                "failure_code": "expected-rejection",
                "fixture": fixture,
                "fixture_sha256": digest,
                "exit_code": 1,
            }
        )

    adv_doc = {
        "schema": "weaver-adversarial-results-1",
        "baseline": {"status": "PASS"},
        "results": cases,
        "status": "PASS",
    }
    write_json(output / "adversarial-results.json", adv_doc)
    files["adversarial-results.json" if outside else "verification-output/adversarial-results.json"] = (
        sha256((output / "adversarial-results.json").read_bytes())
    )
    manifest = {"schema": "weaver-evidence-manifest-1", "files": dict(sorted(files.items()))}
    write_json(output / "evidence-manifest.json", manifest)
    commands = [
        {
            "verifier": item["name"],
            "step": step["step"],
            "command": step["command"],
            "exit_code": step["exit_code"],
            "status": step["status"],
        }
        for item in verifiers
        for step in item["steps"]
    ]
    report = {
        "schema_version": "1.0",
        "repository": "test/repository",
        "source_head_sha": "a" * 40,
        "verified_commit_sha": "b" * 40,
        "base_sha": "c" * 40,
        "dirty": False,
        "created_at": "2026-10-09T00:00:00Z",
        "scope": "local-checks-not-independent-reproduction",
        "lockfile_sha256": files["requirements-verification.lock"],
        "wheel_sha256": files["dist/local_fixture.whl"],
        "environment": {
            "python_version": "synthetic",
            "os": "posix",
            "platform": "synthetic",
            "runner": "synthetic",
        },
        "github_run_id": "synthetic",
        "commands": commands,
        "verifiers": verifiers,
        "adversarial_results": cases,
        "artifact_hashes": manifest["files"],
        "evidence_manifest_sha256": sha256((output / "evidence-manifest.json").read_bytes()),
        "implementation_status": {
            "chronicle": "DEFERRED_TO_BOUND_WITNESS",
            "kernel": "DEFERRED_TO_BOUND_WITNESS",
            "receipt": "DEFERRED_TO_BOUND_WITNESS",
        },
        "overall_verdict": "PASS",
    }
    write_json(output / "verification-report.json", report)
    write_json(output / "report.json", report)
    return root, output


def refresh(root: Path, output: Path, *, manifest: dict | None = None, report: dict | None = None):
    if manifest is None:
        manifest = json.loads((output / "evidence-manifest.json").read_text())
    if report is None:
        report = json.loads((output / "verification-report.json").read_text())
    write_json(output / "evidence-manifest.json", manifest)
    report["artifact_hashes"] = manifest["files"]
    report["evidence_manifest_sha256"] = sha256(
        (output / "evidence-manifest.json").read_bytes()
    )
    write_json(output / "verification-report.json", report)
    write_json(output / "report.json", report)


@pytest.mark.parametrize("outside", [False, True])
def test_intact_bundle_reports_only_local_byte_integrity(tmp_path, outside):
    root, output = fixture_bundle(tmp_path, outside=outside)
    result = verify_bundle(root, output)
    assert result["result"] == "BUNDLE_BYTES_CONSISTENT"
    assert result["assurance"] == "LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION"
    assert result["verifiers_checked"] == 7
    assert result["adversarial_cases_checked"] == 6


def test_tampered_log_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    (output / "unit_and_integration--run.log").write_text("tampered")
    with pytest.raises(BundleRefusal, match="hash mismatch"):
        verify_bundle(root, output)


def test_missing_log_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    (output / "unit_and_integration--run.log").unlink()
    with pytest.raises(BundleRefusal, match="missing or ambiguous"):
        verify_bundle(root, output)


def test_manifest_rewrite_without_report_update_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    manifest = json.loads((output / "evidence-manifest.json").read_text())
    manifest["files"]["pyproject.toml"] = "0" * 64
    write_json(output / "evidence-manifest.json", manifest)
    with pytest.raises(BundleRefusal, match="manifest digest"):
        verify_bundle(root, output)


def test_inconsistent_canonical_and_compatibility_reports_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    (output / "report.json").write_text("{}\n")
    with pytest.raises(BundleRefusal, match="reports differ"):
        verify_bundle(root, output)


def test_report_command_substitution_refused_even_when_both_copies_match(tmp_path):
    root, output = fixture_bundle(tmp_path)
    report = json.loads((output / "verification-report.json").read_text())
    report["commands"][0]["command"] = ["forged-success"]
    refresh(root, output, report=report)
    with pytest.raises(BundleRefusal, match="transcript differs"):
        verify_bundle(root, output)


def test_step_log_substitution_refused_even_when_report_copies_match(tmp_path):
    root, output = fixture_bundle(tmp_path)
    report = json.loads((output / "verification-report.json").read_text())
    report["verifiers"][0]["steps"][0]["log_sha256"] = "0" * 64
    refresh(root, output, report=report)
    with pytest.raises(BundleRefusal, match="step log digest"):
        verify_bundle(root, output)


def test_absolute_or_parent_traversal_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    manifest = json.loads((output / "evidence-manifest.json").read_text())
    manifest["files"]["../bypass.txt"] = "0" * 64
    refresh(root, output, manifest=manifest)
    with pytest.raises(BundleRefusal, match="path traversal"):
        verify_bundle(root, output)


def test_duplicate_json_keys_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    (output / "evidence-manifest.json").write_text(
        '{"schema":"weaver-evidence-manifest-1","schema":"weaver-evidence-manifest-1","files":{}}'
    )
    with pytest.raises(BundleRefusal, match="duplicate JSON member"):
        verify_bundle(root, output)


def test_external_shadowed_source_refused_even_with_identical_bytes(tmp_path):
    root, output = fixture_bundle(tmp_path, outside=True)
    shutil.copy2(root / "pyproject.toml", output / "pyproject.toml")
    with pytest.raises(BundleRefusal, match="ambiguous"):
        verify_bundle(root, output)


def test_symlinked_source_artifact_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    lock = root / "requirements-verification.lock"
    real = root / "actual.lock"
    lock.rename(real)
    lock.symlink_to(real)
    with pytest.raises(BundleRefusal, match="symlink"):
        verify_bundle(root, output)


def test_untracked_output_file_refused(tmp_path):
    root, output = fixture_bundle(tmp_path)
    (output / "untracked.log").write_text("untracked")
    with pytest.raises(BundleRefusal, match="untracked"):
        verify_bundle(root, output)


def test_forged_adversarial_result_detected_when_hashes_recomputed(tmp_path):
    root, output = fixture_bundle(tmp_path)
    adv = json.loads((output / "adversarial-results.json").read_text())
    adv["results"][0]["case_name"] = "forged"
    write_json(output / "adversarial-results.json", adv)
    manifest = json.loads((output / "evidence-manifest.json").read_text())
    manifest["files"]["verification-output/adversarial-results.json"] = sha256(
        (output / "adversarial-results.json").read_bytes()
    )
    refresh(root, output, manifest=manifest)
    with pytest.raises(BundleRefusal, match="adversarial results differ"):
        verify_bundle(root, output)


def test_reported_wheel_digest_must_match_artifact(tmp_path):
    root, output = fixture_bundle(tmp_path)
    report = json.loads((output / "verification-report.json").read_text())
    report["wheel_sha256"] = "0" * 64
    refresh(root, output, report=report)
    with pytest.raises(BundleRefusal, match="wheel SHA-256"):
        verify_bundle(root, output)


def test_reported_failure_never_admitted_as_positive_result(tmp_path):
    root, output = fixture_bundle(tmp_path)
    report = json.loads((output / "verification-report.json").read_text())
    report["overall_verdict"] = "FAIL"
    refresh(root, output, report=report)
    with pytest.raises(BundleRefusal, match="producer overall verdict"):
        verify_bundle(root, output)
