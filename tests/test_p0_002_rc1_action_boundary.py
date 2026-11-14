"""P0-002: regression coverage for the maintained, frozen RC1 action boundary.

These tests exercise the adapter and release bytes currently present in Weaver_Os.
They do NOT execute or apply historical P0-001 patches, and they confer no authority.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.witness_rc1_state_adapter import build_envelope

COMMAND = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "witness_rc1_authorized_command.json"
)


def command_document() -> dict:
    return json.loads(COMMAND.read_text(encoding="utf-8"))


def test_exact_allowed_action_retains_bounded_simulation_behavior() -> None:
    result = build_envelope(command_document())
    state = result["state"]
    assert state["last_verdict"] == "ACCEPT"
    assert state["protected"] == {"counter": 1}
    assert state["used_command_ids"] == ["C1"]
    assert state["chronicle_entries"][-1]["event"]["reasons"] == []


@pytest.mark.parametrize(
    "unlisted_action",
    (
        "",
        "INCREMENT",
        "set",
        "reset",
        "increment_production",
        "increment-and-commit",
    ),
)
def test_unlisted_action_refused_without_protected_state_mutation(
    unlisted_action: str,
) -> None:
    document = command_document()
    document["cmd"]["action"] = unlisted_action
    original = copy.deepcopy(document)

    result = build_envelope(document)
    state = result["state"]
    event = state["chronicle_entries"][-1]["event"]
    receipt = state["last_receipt"]

    assert document == original  # adapter does not rewrite proposal
    assert state["last_verdict"] == "REJECT"
    assert state["protected"] == {"counter": 0}
    assert state["used_command_ids"] == []
    assert len(state["chronicle_entries"]) == 1
    assert event["verdict"] == "REJECT"
    assert event["reasons"] == ["action_mismatch"]
    assert event["state_before"] == event["state_after"]
    assert receipt["verdict"] == "REJECT"
    assert receipt["state_before"] == receipt["state_after"]


def test_unauthorized_allowlisted_action_is_refused_without_consuming_id() -> None:
    document = command_document()
    document["cmd"]["authorized"] = False

    state = build_envelope(document)["state"]
    event = state["chronicle_entries"][-1]["event"]

    assert state["last_verdict"] == "REJECT"
    assert state["protected"] == {"counter": 0}
    assert state["used_command_ids"] == []
    assert event["reasons"] == ["unauthorized"]
    assert event["state_before"] == event["state_after"]


def test_allowed_action_wrong_target_is_refused_without_consuming_id() -> None:
    document = command_document()
    document["cmd"]["target"] = "unrelated.counter"

    state = build_envelope(document)["state"]
    event = state["chronicle_entries"][-1]["event"]

    assert state["last_verdict"] == "REJECT"
    assert state["protected"] == {"counter": 0}
    assert state["used_command_ids"] == []
    assert event["reasons"] == ["target_mismatch"]
    assert event["state_before"] == event["state_after"]
