from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.authority_state import AuthorityStateError, replay_authority_state

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIGEST = "39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e"


def load_ledger():
    return json.loads((ROOT / "authority_ledger.json").read_text(encoding="utf-8"))


def payload(event):
    return json.loads(event["payload"])


def encode_payload(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def test_known_authority_state_projection_and_digest():
    result = replay_authority_state(load_ledger())
    assert result.state == {
        "receipt_id": "AL-ADOC-2026-001",
        "state": "EXECUTED",
    }
    assert result.digest == EXPECTED_DIGEST
    assert result.method == "authority-transition-reducer-v1"
    assert result.events == 6


def test_state_discontinuity_is_rejected():
    ledger = load_ledger()
    changed = copy.deepcopy(ledger)
    item = payload(changed[3])
    item["current_state"] = "WRONG"
    changed[3]["payload"] = encode_payload(item)

    with pytest.raises(AuthorityStateError, match="state discontinuity"):
        replay_authority_state(changed)


def test_receipt_identity_switch_is_rejected():
    ledger = load_ledger()
    changed = copy.deepcopy(ledger)
    item = payload(changed[2])
    item["receipt_id"] = "OTHER"
    changed[2]["payload"] = encode_payload(item)

    with pytest.raises(AuthorityStateError, match="receipt_id changed"):
        replay_authority_state(changed)


def test_malformed_payload_is_rejected():
    ledger = load_ledger()
    changed = copy.deepcopy(ledger)
    changed[-1]["payload"] += "\nnot-json"

    with pytest.raises(AuthorityStateError, match="invalid payload JSON"):
        replay_authority_state(changed)


def test_unrecognized_payload_field_is_rejected():
    ledger = load_ledger()
    changed = copy.deepcopy(ledger)
    item = payload(changed[0])
    item["silent_authority"] = True
    changed[0]["payload"] = encode_payload(item)

    with pytest.raises(AuthorityStateError, match="unrecognized fields"):
        replay_authority_state(changed)


def test_noop_transition_is_rejected():
    ledger = load_ledger()
    changed = copy.deepcopy(ledger)
    item = payload(changed[1])
    item["target_state"] = item["current_state"]
    changed[1]["payload"] = encode_payload(item)

    with pytest.raises(AuthorityStateError, match="no-op transition"):
        replay_authority_state(changed)
