"""P0-010: malformed verifier outcomes never masquerade as admission.

RED controls exercise the exact PR #91 aggregate decision helper. Successful
schema validation elsewhere must not compensate for a permissive gate here.
These are same-origin synthetic tests, not external witnessing or authority.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from tools.check_e35_withheld import E35_REQUIRED, LOCAL_REQUIRED, classify
from tools.verify_all import REQUIRED_VERIFIERS, is_valid_verdict


def good_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    verifiers = [
        {
            "name": name,
            "status": "PASS",
            "exit_code": 0,
            "steps": [{"step": "run", "status": "PASS", "exit_code": 0}],
        }
        for name in REQUIRED_VERIFIERS
    ]
    adversarial = [
        {
            "case_id": f"ADV-{index:03d}",
            "status": "PASS",
            "expected_verdict": "REJECT",
            "observed_verdict": "REJECT",
            "exit_code": 1,
            "failure_code": "synthetic expected refusal",
        }
        for index in range(1, 7)
    ]
    return verifiers, adversarial


def test_positive_aggregate_control_is_still_accepted():
    verifiers, cases = good_inputs()
    assert is_valid_verdict(verifiers, cases, "a" * 64)


@pytest.mark.parametrize("bad", [False, True, 0.0, "0"])
@pytest.mark.parametrize("scope", ["verifier", "step"])
def test_false_green_exit_code_substitutions_refused(scope: str, bad: Any):
    verifiers, cases = good_inputs()
    if scope == "verifier":
        verifiers[0]["exit_code"] = bad
    else:
        verifiers[0]["steps"][0]["exit_code"] = bad
    assert not is_valid_verdict(verifiers, cases, "a" * 64)


@pytest.mark.parametrize(
    "mutant",
    [
        "null_verifier",
        "non_mapping_step",
        "unhashable_verifier_name",
        "null_case",
        "unhashable_case_id",
        "non_list_verifiers",
        "non_list_cases",
        "non_mapping_verifiers",
        "non_mapping_cases",
    ],
)
def test_malformed_gate_inputs_refuse_without_crashing(mutant: str):
    verifiers, cases = good_inputs()
    if mutant == "null_verifier":
        verifiers[0] = None  # type: ignore[call-overload]
    elif mutant == "non_mapping_step":
        verifiers[0]["steps"][0] = None
    elif mutant == "unhashable_verifier_name":
        verifiers[0]["name"] = ["not-a-string"]
    elif mutant == "null_case":
        cases[0] = None  # type: ignore[call-overload]
    elif mutant == "unhashable_case_id":
        cases[0]["case_id"] = ["not-a-string"]
    elif mutant == "non_list_verifiers":
        verifiers = None  # type: ignore[assignment]
    elif mutant == "non_list_cases":
        cases = None  # type: ignore[assignment]
    elif mutant == "non_mapping_verifiers":
        verifiers = {}  # type: ignore[assignment]
    else:
        cases = {}  # type: ignore[assignment]
    assert not is_valid_verdict(verifiers, cases, "a" * 64)


def test_successful_refusal_gate_does_not_grant_refused_level():
    local = subprocess.CompletedProcess(
        ["synthetic-local"], 0, "\n".join(LOCAL_REQUIRED) + "\n", ""
    )
    withheld = subprocess.CompletedProcess(
        ["synthetic-e35"], 1, "\n".join(E35_REQUIRED) + "\n", ""
    )
    assert classify(local, withheld) == []
    # A missing-dependency failure is not an acceptable substitute for refusal.
    missing_dependency = subprocess.CompletedProcess(
        ["synthetic-e35"], 1, "", "ModuleNotFoundError: jsonschema"
    )
    assert classify(local, missing_dependency)
