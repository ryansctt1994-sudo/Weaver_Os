"""P0-009: jointly exercise the PR #88 adversarial semantics and PR #90 JSON gate.

This checks coexistence in one tested source tree. It is NOT independent
reproduction, witness admission, source authentication, or merge permission.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import verify_attestations
from tools.verify_all import REQUIRED_VERIFIERS, is_valid_verdict
from tools.witness_policy_freeze import adjudication_record

ZERO64 = "0" * 64


def _verifiers() -> list[dict]:
    return [
        {
            "name": name,
            "status": "PASS",
            "exit_code": 0,
            "steps": [{"step": "run", "exit_code": 0, "status": "PASS"}],
        }
        for name in REQUIRED_VERIFIERS
    ]


def _cases() -> list[dict]:
    return [
        {
            "case_id": f"ADV-{index:03d}",
            "status": "PASS",
            "expected_verdict": "REJECT",
            "observed_verdict": "REJECT",
            "exit_code": 1,
            "failure_code": "expected rejection",
        }
        for index in range(1, 7)
    ]


def test_strict_json_and_adversarial_verdict_operate_together(tmp_path: Path):
    path = tmp_path / "adversarial.json"
    # Equivalent decoded keys, regardless of escape spelling, must be rejected.
    path.write_text(
        '{"result":{"status":"PASS","stat\\u0075s":"FAIL"}}', encoding="utf-8"
    )
    with pytest.raises(verify_attestations.VerificationError, match="DUPLICATE_KEY"):
        verify_attestations.load_json(path)

    verifiers, cases = _verifiers(), _cases()
    assert is_valid_verdict(verifiers, cases, ZERO64)

    # A consistent digest alone cannot convert a wrong adversarial outcome
    # into successful rejection. The semantics are independently checked.
    cases[0]["observed_verdict"] = "UNEXPECTED_PASS"
    assert not is_valid_verdict(verifiers, cases, ZERO64)


def test_clean_json_valid_but_policy_freeze_remains_withheld(tmp_path: Path):
    path = tmp_path / "clean.json"
    path.write_text('{"result":{"status":"PASS"}}', encoding="utf-8")
    assert verify_attestations.load_json(path) == {"result": {"status": "PASS"}}

    policy = adjudication_record()
    assert policy["status"] == "DISCREPANCY_UNADJUDICATED"
    assert policy["governing_policy"] is None
    assert policy["release_target_frozen"] is False
    assert len(policy["declared_policies"]) == 4
