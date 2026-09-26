import copy
import json
from pathlib import Path

import pytest

from demo.denial_bridge import check_denied_projection, project, replay
from demo.e2e_transaction import digest, initial_state, transition

CASES = Path(__file__).resolve().parents[1] / "demo" / "demo_cases"


def transaction(name, state):
    tx = json.loads((CASES / name).read_text())
    tx["from_state_hash"] = digest(state)
    return tx


def test_projection_covers_every_protected_field():
    state = initial_state()
    baseline = project(state)
    for altered in (
        {**state, "authority": 1},
        {**state, "artifact": "x"},
        {**state, "revision": 1},
    ):
        assert project(altered) != baseline
    with pytest.raises(ValueError):
        project({**state, "unmapped": 1})
    with pytest.raises(ValueError):
        project({**state, "revision": True})


def test_real_denial_matches_identity_step_after_nonvacuous_accept():
    start = initial_state()
    valid = transaction("01_valid_ordinary_proposal.json", start)
    committed, accepted = transition(start, valid)
    assert accepted["verdict"] == "ACCEPT" and committed != start
    rejected = transaction("02_authority_leak_attempt.json", committed)
    after, receipt = check_denied_projection(committed, rejected)
    assert receipt["code"] == "AUTHORITY_ERROR"
    assert after == committed
    # The separate chronicle may append a rejected record; it is not in `project`.


def test_bridge_detects_runtime_mutation_even_when_receipt_says_reject():
    state = initial_state()
    tx = transaction("02_authority_leak_attempt.json", state)

    def broken(s, proposal):
        after, receipt = transition(s, proposal)
        after["revision"] += 1
        return after, receipt

    with pytest.raises(AssertionError, match="changed protected state"):
        check_denied_projection(state, tx, runtime=broken)


def test_replay_append_for_frozen_fixture_sequence():
    start = initial_state()
    valid = transaction("01_valid_ordinary_proposal.json", start)
    committed, _ = transition(start, valid)
    denied = transaction("02_authority_leak_attempt.json", committed)
    sequence = [valid, denied]
    full = replay(start, sequence)
    for split in range(3):
        assert full == replay(replay(start, sequence[:split]), sequence[split:])
    assert full == committed


def test_denial_input_is_not_mutated():
    state = initial_state()
    tx = transaction("02_authority_leak_attempt.json", state)
    frozen = copy.deepcopy((state, tx))
    check_denied_projection(state, tx)
    assert (state, tx) == frozen
