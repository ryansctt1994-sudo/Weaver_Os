from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tools.runtime_state_digest import (
    RuntimeStateError,
    observe_runtime_state,
    parse_runtime_envelope,
    state_digest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "runtime_state_emitter.py"


def test_state_digest_is_key_order_stable():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert state_digest(left) == state_digest(right)


def test_state_change_changes_digest():
    assert state_digest({"counter": 1}) != state_digest({"counter": 2})


def test_fixture_runtime_observation_is_bound():
    observation = observe_runtime_state(
        [sys.executable, str(FIXTURE)],
        expected_runtime_id="fixture-runtime",
        expected_binding_kind="git_commit",
        expected_binding_value="1" * 40,
        expected_replay_input_digest="2" * 64,
    )
    assert observation.runtime_id == "fixture-runtime"
    assert observation.source_binding_value == "1" * 40
    assert observation.replay_input_digest == "2" * 64
    assert len(observation.state_digest) == 64


def test_source_binding_substitution_is_rejected():
    with pytest.raises(RuntimeStateError, match="SOURCE_BINDING_VALUE_MISMATCH"):
        observe_runtime_state(
            [sys.executable, str(FIXTURE)],
            expected_runtime_id="fixture-runtime",
            expected_binding_kind="git_commit",
            expected_binding_value="3" * 40,
            expected_replay_input_digest="2" * 64,
        )


def test_replay_input_substitution_is_rejected():
    with pytest.raises(RuntimeStateError, match="REPLAY_INPUT_DIGEST_MISMATCH"):
        observe_runtime_state(
            [sys.executable, str(FIXTURE)],
            expected_runtime_id="fixture-runtime",
            expected_binding_kind="git_commit",
            expected_binding_value="1" * 40,
            expected_replay_input_digest="4" * 64,
        )


def test_runtime_id_substitution_is_rejected():
    with pytest.raises(RuntimeStateError, match="RUNTIME_ID_MISMATCH"):
        observe_runtime_state(
            [sys.executable, str(FIXTURE)],
            expected_runtime_id="other-runtime",
            expected_binding_kind="git_commit",
            expected_binding_value="1" * 40,
            expected_replay_input_digest="2" * 64,
        )


def test_extra_runtime_output_field_is_rejected():
    raw = json.dumps(
        {
            "schema": "weaver-runtime-state-1",
            "runtime_id": "fixture-runtime",
            "source_binding": {"kind": "git_commit", "value": "1" * 40},
            "replay_input_digest": "2" * 64,
            "state": {},
            "unexpected": True,
        }
    ).encode()
    with pytest.raises(RuntimeStateError, match="RUNTIME_OUTPUT_FIELDS_UNRECOGNIZED"):
        parse_runtime_envelope(raw)


def test_runtime_state_must_be_an_object():
    raw = json.dumps(
        {
            "schema": "weaver-runtime-state-1",
            "runtime_id": "fixture-runtime",
            "source_binding": {"kind": "git_commit", "value": "1" * 40},
            "replay_input_digest": "2" * 64,
            "state": ["not", "an", "object"],
        }
    ).encode()
    with pytest.raises(RuntimeStateError, match="RUNTIME_STATE_NOT_OBJECT"):
        parse_runtime_envelope(raw)
