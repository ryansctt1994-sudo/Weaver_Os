import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
EVENT_SCHEMA_PATH = ROOT / "schemas" / "triad_event.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "triad_receipt.schema.json"


def load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def event_validator() -> Draft202012Validator:
    schema = load_schema(EVENT_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def receipt_validator() -> Draft202012Validator:
    schema = load_schema(RECEIPT_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def valid_event() -> dict:
    return {
        "index": 0,
        "timestamp": "2026-06-06T22:15:30.123456Z",
        "event_type": "proposal",
        "actor": "user123",
        "public_key": "1a2b3c",
        "payload": {
            "id": "p1",
            "action": "update_config",
            "value": 0.8,
            "rationale": "User requested higher creativity",
        },
        "prev_hash": "genesis",
        "event_hash": "8f4a2b",
        "signature": "e3f7c9",
        "policy_version": "policy-v1",
    }


@pytest.fixture
def valid_receipt() -> dict:
    return {
        "receipt_id": "r1",
        "proposal_hash": "proposalhash",
        "event_hash": "8f4a2b",
        "replay_root": "8f4a2b",
        "timestamp": "2026-06-06T22:16:00.000000Z",
        "witness_summary": {
            "composite_flags": ["no_dissent"],
            "dissent_count": 0,
        },
        "receipt_hash": "receipthash",
    }


def assert_valid(validator: Draft202012Validator, instance: dict) -> None:
    validator.validate(instance)


def assert_invalid(validator: Draft202012Validator, instance: dict) -> None:
    with pytest.raises(ValidationError):
        validator.validate(instance)


def test_valid_event_schema_round_trip(event_validator, valid_event):
    encoded = json.dumps(valid_event, sort_keys=True)
    decoded = json.loads(encoded)

    assert_valid(event_validator, decoded)


def test_event_requires_policy_version(event_validator, valid_event):
    event = deepcopy(valid_event)
    event.pop("policy_version")

    assert_invalid(event_validator, event)


def test_event_rejects_invalid_event_type(event_validator, valid_event):
    event = deepcopy(valid_event)
    event["event_type"] = "authorized_without_replay"

    assert_invalid(event_validator, event)


def test_event_rejects_additional_properties(event_validator, valid_event):
    event = deepcopy(valid_event)
    event["silent_authority"] = True

    assert_invalid(event_validator, event)


def test_valid_lightweight_receipt_schema_round_trip(receipt_validator, valid_receipt):
    encoded = json.dumps(valid_receipt, sort_keys=True)
    decoded = json.loads(encoded)

    assert_valid(receipt_validator, decoded)


def test_receipt_rejects_missing_event_hash(receipt_validator, valid_receipt):
    receipt = deepcopy(valid_receipt)
    receipt.pop("event_hash")

    assert_invalid(receipt_validator, receipt)


def test_receipt_rejects_malformed_witness_summary(receipt_validator, valid_receipt):
    receipt = deepcopy(valid_receipt)
    receipt["witness_summary"] = {
        "composite_flags": ["dissent_present"],
        "dissent_count": "one",
    }

    assert_invalid(receipt_validator, receipt)


def test_receipt_rejects_additional_properties(receipt_validator, valid_receipt):
    receipt = deepcopy(valid_receipt)
    receipt["unbound_authority_claim"] = "approved"

    assert_invalid(receipt_validator, receipt)
