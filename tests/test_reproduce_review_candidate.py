"""Operator preflight and fail-closed aggregate replay controls (same-author)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import reproduce_review_candidate as operator
from tools.verify_evidence_bundle import BundleRefusal


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def detached_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "checkout"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "runner@example.invalid")
    git(root, "config", "user.name", "Synthetic CI")
    (root / ".gitignore").write_text("verification-output/\n", encoding="utf-8")
    (root / "requirements-verification.lock").write_text("synthetic lock\n", encoding="utf-8")
    script = root / "tools" / "reproduce_review_candidate.py"
    script.parent.mkdir()
    script.write_text("synthetic pinned tool bytes\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "-c", "commit.gpgsign=false", "commit", "-qm", "synthetic pinned checkout")
    head = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "--detach", "-q", head)
    return root, head


def test_clean_detached_full_sha_is_admitted(detached_repo):
    root, head = detached_repo
    assert operator.preflight(root, head) == head


@pytest.mark.parametrize("head", ["", "a" * 39, "A" * 40, "0" * 40, "main"])
def test_wrong_or_ambiguous_source_ref_refused(detached_repo, head):
    root, correct = detached_repo
    if head == correct:
        pytest.skip("synthetic collision, not expected")
    with pytest.raises(operator.ReproductionRefusal):
        operator.preflight(root, head)


def test_attached_branch_is_not_frozen(detached_repo):
    root, head = detached_repo
    git(root, "checkout", "-q", "-b", "attached")
    with pytest.raises(operator.ReproductionRefusal, match="detached"):
        operator.preflight(root, head)


@pytest.mark.parametrize("mutation", ["tracked", "untracked"])
def test_dirty_source_refused(detached_repo, mutation):
    root, head = detached_repo
    path = root / (".gitignore" if mutation == "tracked" else "unexpected.txt")
    path.write_text("unbound source\n", encoding="utf-8")
    with pytest.raises(operator.ReproductionRefusal, match="dirty"):
        operator.preflight(root, head)


def test_existing_output_refused_even_if_ignored(detached_repo):
    root, head = detached_repo
    (root / "verification-output").mkdir()
    with pytest.raises(operator.ReproductionRefusal, match="stale"):
        operator.reproduce(root, head)


def scripted_verifier(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    head: str,
    *,
    returncode: Any = 0,
    report_head: str | None = None,
    bundle: dict[str, Any] | None = None,
) -> list[list[str]]:
    """Stub costly verifier execution; real Git preflight and final byte hashes remain."""
    real_run = subprocess.run
    observed: list[list[str]] = []

    def run(command, *args, **kwargs):
        if (
            isinstance(command, list)
            and len(command) >= 3
            and command[1:3] == ["-m", "tools.verify_all"]
        ):
            observed.append(command)
            out = root / "verification-output"
            out.mkdir(exist_ok=True)
            (out / "evidence-manifest.json").write_text("synthetic manifest\n")
            (out / "verification-report.json").write_text(
                json.dumps(
                    {
                        "source_head_sha": report_head or head,
                        "verified_commit_sha": report_head or head,
                        "dirty": False,
                        "overall_verdict": "PASS",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, returncode, "", "")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(operator.subprocess, "run", run)
    monkeypatch.setattr(
        operator,
        "verify_bundle",
        lambda _root, output: bundle
        or {
            "result": "BUNDLE_BYTES_CONSISTENT",
            "assurance": operator.ASSURANCE,
            "files_checked": 35,
            "verifiers_checked": 7,
            "adversarial_cases_checked": 6,
            "manifest_sha256": operator._sha256(output / "evidence-manifest.json"),
        },
    )
    return observed


def test_success_still_withholds_witness(detached_repo, monkeypatch):
    root, head = detached_repo
    commands = scripted_verifier(monkeypatch, root, head)
    receipt = operator.reproduce(root, head)
    assert len(commands) == 1
    assert receipt["result"] == "LOCAL_VERIFICATION_REPRODUCED"
    assert receipt["source"]["expected_commit_sha"] == head
    assert receipt["source"]["observed_commit_sha"] == head
    assert receipt["evidence"]["verifiers_checked"] == 7
    assert receipt["trust"]["authenticated_witness"] is False
    assert receipt["trust"]["independence_verified"] is False
    assert receipt["trust"]["witness"] == "W0"
    assert receipt["trust"]["production"] == "PROHIBITED"


@pytest.mark.parametrize("exit_code", [1, False, 0.0])
def test_nonliteral_zero_or_failed_execution_cannot_pass(detached_repo, monkeypatch, exit_code):
    root, head = detached_repo
    scripted_verifier(monkeypatch, root, head, returncode=exit_code)
    with pytest.raises(operator.ReproductionRefusal, match="complete verifier refused"):
        operator.reproduce(root, head)


def test_successful_execution_cannot_hide_wrong_report_head(detached_repo, monkeypatch):
    root, head = detached_repo
    scripted_verifier(monkeypatch, root, head, report_head="f" * 40)
    with pytest.raises(operator.ReproductionRefusal, match="both commit claims"):
        operator.reproduce(root, head)


def test_false_consumer_assurance_cannot_pass(detached_repo, monkeypatch):
    root, head = detached_repo
    scripted_verifier(
        monkeypatch,
        root,
        head,
        bundle={
            "result": "BUNDLE_BYTES_CONSISTENT",
            "assurance": "INDEPENDENT_WITNESS",
            "files_checked": 35,
            "verifiers_checked": 7,
            "adversarial_cases_checked": 6,
            "manifest_sha256": "a" * 64,
        },
    )
    with pytest.raises(operator.ReproductionRefusal, match="bounded expected"):
        operator.reproduce(root, head)


def test_consumer_refusal_is_not_turned_into_success(detached_repo, monkeypatch):
    root, head = detached_repo
    scripted_verifier(monkeypatch, root, head)

    def refuse(_root, _output):
        raise BundleRefusal("tampered report")

    monkeypatch.setattr(operator, "verify_bundle", refuse)
    with pytest.raises(BundleRefusal, match="tampered"):
        operator.reproduce(root, head)


def test_source_change_during_execution_refused(detached_repo, monkeypatch):
    root, head = detached_repo
    commands = scripted_verifier(monkeypatch, root, head)
    original_run = operator.subprocess.run

    def mutate(command, *args, **kwargs):
        result = original_run(command, *args, **kwargs)
        if command[1:3] == ["-m", "tools.verify_all"]:
            (root / ".gitignore").write_text("mutation inside execution\n")
        return result

    monkeypatch.setattr(operator.subprocess, "run", mutate)
    with pytest.raises(operator.ReproductionRefusal, match="dirty"):
        operator.reproduce(root, head)
    assert len(commands) == 1
