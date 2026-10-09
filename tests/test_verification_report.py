"""The aggregate report can only claim PASS when closure is mechanically complete."""

from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from tools.verify_all import REQUIRED_VERIFIERS, is_valid_verdict

ZERO40 = "0" * 40
ZERO64 = "0" * 64


def step(name: str = "run") -> dict:
    return {
        "step": name,
        "command": ["synthetic-test"],
        "exit_code": 0,
        "status": "PASS",
        "log": f"{name}.log",
        "log_sha256": ZERO64,
    }


def verifier(name: str) -> dict:
    return {"name": name, "status": "PASS", "exit_code": 0, "steps": [step()]}


def adversarial(index: int) -> dict:
    return {
        "case_id": f"ADV-{index:03d}",
        "case_name": f"case-{index}",
        "expected_verdict": "REJECT",
        "observed_verdict": "REJECT",
        "status": "PASS",
        "failure_code": "expected rejection",
        "fixture": f"case-{index}.json",
        "fixture_sha256": ZERO64,
        "exit_code": 1,
    }


def valid_report() -> dict:
    verifiers = [verifier(name) for name in REQUIRED_VERIFIERS]
    return {
        "schema_version": "1.0",
        "repository": "test/repo",
        "source_head_sha": ZERO40,
        "verified_commit_sha": ZERO40,
        "base_sha": ZERO40,
        "dirty": False,
        "created_at": "2026-10-04T00:00:00Z",
        "scope": "local-checks-not-independent-reproduction",
        "lockfile_sha256": ZERO64,
        "wheel_sha256": ZERO64,
        "environment": {
            "python_version": "synthetic-test",
            "os": "posix",
            "platform": "synthetic-test",
            "runner": "synthetic-test",
        },
        "github_run_id": "synthetic-test",
        "commands": [
            {
                "verifier": item["name"],
                "step": "run",
                "command": ["synthetic-test"],
                "exit_code": 0,
                "status": "PASS",
            }
            for item in verifiers
        ],
        "verifiers": verifiers,
        "adversarial_results": [adversarial(index) for index in range(1, 7)],
        "artifact_hashes": {
            "a": ZERO64,
            "b": ZERO64,
            "c": ZERO64,
            "d": ZERO64,
            "e": ZERO64,
        },
        "evidence_manifest_sha256": ZERO64,
        "implementation_status": {
            "chronicle": "DEFERRED_TO_BOUND_WITNESS",
            "kernel": "DEFERRED_TO_BOUND_WITNESS",
            "receipt": "DEFERRED_TO_BOUND_WITNESS",
        },
        "overall_verdict": "PASS",
    }


@pytest.fixture
def schema():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "schemas" / "verification_run.schema.json").read_text())


def test_valid_complete_report(schema):
    report = valid_report()
    Draft202012Validator(schema).validate(report)
    assert is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


@pytest.mark.parametrize("missing", REQUIRED_VERIFIERS)
def test_missing_required_verifier_rejected(schema, missing):
    report = valid_report()
    report["verifiers"] = [item for item in report["verifiers"] if item["name"] != missing]
    report["overall_verdict"] = "FAIL"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


def test_failed_verifier_cannot_claim_pass(schema):
    report = valid_report()
    target = report["verifiers"][0]
    target["status"] = "FAIL"
    target["exit_code"] = 2
    target["steps"][0]["status"] = "FAIL"
    target["steps"][0]["exit_code"] = 2
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


def test_missing_wheel_digest_cannot_claim_pass(schema):
    report = valid_report()
    report["wheel_sha256"] = None
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


def test_missing_adversarial_case_rejected(schema):
    report = valid_report()
    report["adversarial_results"].pop()
    report["overall_verdict"] = "FAIL"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


def test_fail_report_is_schema_valid_when_a_required_verifier_fails(schema):
    report = valid_report()
    target = report["verifiers"][0]
    target["status"] = "FAIL"
    target["exit_code"] = 3
    target["steps"][0]["status"] = "FAIL"
    target["steps"][0]["exit_code"] = 3
    report["commands"][0]["status"] = "FAIL"
    report["commands"][0]["exit_code"] = 3
    report["overall_verdict"] = "FAIL"
    Draft202012Validator(schema).validate(report)


def test_dirty_tree_cannot_claim_pass(schema):
    report = valid_report()
    report["dirty"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)
    assert not is_valid_verdict(
        report["verifiers"],
        report["adversarial_results"],
        report["wheel_sha256"],
        dirty=True,
    )


def test_non_hex_wheel_digest_cannot_claim_pass():
    report = valid_report()
    assert not is_valid_verdict(
        report["verifiers"],
        report["adversarial_results"],
        "g" * 64,
    )


def test_unknown_top_level_field_rejected(schema):
    report = deepcopy(valid_report())
    report["authority"] = "production"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(report)


def test_duplicate_cannot_hide_failed_verifier():
    report = valid_report()
    failed = dict(report["verifiers"][0], status="FAIL", exit_code=3)
    report["verifiers"].insert(0, failed)
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


@pytest.mark.parametrize(
    "mutation", ["nonzero_step", "failed_step", "no_steps", "nonzero_verifier"]
)
def test_pass_label_cannot_hide_failed_execution(mutation):
    report = valid_report()
    item = report["verifiers"][0]
    if mutation == "nonzero_step":
        item["steps"][0]["exit_code"] = 3
    elif mutation == "failed_step":
        item["steps"][0]["status"] = "FAIL"
    elif mutation == "no_steps":
        item["steps"] = []
    else:
        item["exit_code"] = 3
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )


def test_duplicate_adversarial_result_is_refused():
    report = valid_report()
    report["adversarial_results"].append(deepcopy(report["adversarial_results"][0]))
    assert not is_valid_verdict(
        report["verifiers"], report["adversarial_results"], report["wheel_sha256"]
    )
