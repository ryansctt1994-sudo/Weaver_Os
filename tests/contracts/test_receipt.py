import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest
from weaver_contracts import receipt as r

SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "packages/contracts/weaver_contracts/schemas/wx_receipt_1.schema.json"
    ).read_text(encoding="utf-8")
)


def _fields(**overrides):
    base = {
        "ledger_id": "wx-main",
        "root": "AUTHORITY",
        "sequence": 0,
        "predecessor_digest": r.GENESIS_DIGEST,
        "event_type": "STATE_TRANSITION",
        "event_digest": "ab" * 32,
        "actor_id": "op-1",
        "policy_version": "policy-v1",
        "admissibility": "ADMITTED",
        "reason_code": None,
        "committed_at": "2026-11-07T09:00:00Z",
    }
    base.update(overrides)
    return base


def _rejection(**overrides):
    return _fields(
        root="REJECTION",
        sequence=1,
        predecessor_digest="cd" * 32,
        admissibility="REJECTED",
        reason_code="INVALID_SIGNATURE",
        **overrides,
    )


def _with(receipt, **changes):
    data = receipt.to_dict()
    data.update(changes)
    return data


def test_genesis_receipt_round_trips_and_matches_schema():
    receipt = r.build(**_fields())
    assert r.from_dict(receipt.to_dict()) == receipt
    jsonschema.validate(receipt.to_dict(), SCHEMA)


def test_digest_is_pinned_for_a_fixed_body():
    receipt = r.build(**_fields())
    assert receipt.receipt_digest == (
        "8cd2349934be732881a1cbd9e9e851c12e68bfb0ad7aefabe247172ac3544d3e"
    )


def test_rejection_receipt_is_valid():
    receipt = r.build(**_rejection())
    jsonschema.validate(receipt.to_dict(), SCHEMA)
    assert receipt.root == "REJECTION"


def test_canonical_bytes_are_stable():
    receipt = r.build(**_fields())
    assert receipt.to_canonical() == r.build(**_fields()).to_canonical()
    assert json.loads(receipt.to_canonical()) == receipt.to_dict()


def test_tampered_field_breaks_digest():
    receipt = r.build(**_fields())
    with pytest.raises(r.ReceiptError, match="does not match"):
        r.from_dict(_with(receipt, actor_id="op-2"))


def test_failed_action_cannot_be_state():
    with pytest.raises(r.ReceiptError, match="AUTHORITY root requires"):
        r.build(**_fields(admissibility="REJECTED", reason_code="POLICY"))


def test_rejection_root_cannot_hold_admitted_event():
    with pytest.raises(r.ReceiptError, match="REJECTION root requires"):
        r.build(**_rejection(**{}) | {"admissibility": "ADMITTED", "reason_code": None})


def test_rejection_needs_reason_code():
    with pytest.raises(r.ReceiptError, match="reason_code"):
        r.build(**_rejection() | {"reason_code": None})


def test_admitted_must_not_carry_reason_code():
    with pytest.raises(r.ReceiptError, match="reason_code"):
        r.build(**_fields(reason_code="SHOULD_NOT_BE_HERE"))


@pytest.mark.parametrize(
    "sequence, predecessor",
    [(0, "ab" * 32), (1, r.GENESIS_DIGEST)],
)
def test_genesis_rule(sequence, predecessor):
    with pytest.raises(r.ReceiptError, match="genesis"):
        r.build(**_fields(sequence=sequence, predecessor_digest=predecessor))


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"sequence": -1}, "sequence"),
        ({"sequence": True}, "sequence"),
        ({"event_digest": "AB" * 32}, "event_digest"),
        ({"event_digest": "ab" * 31}, "event_digest"),
        ({"event_type": "state_transition"}, "event_type"),
        ({"actor_id": "TBD"}, "placeholder"),
        ({"actor_id": ""}, "actor_id"),
        ({"committed_at": "2026-11-07T09:00:00+00:00"}, "committed_at"),
        ({"committed_at": "2026-11-07T09:00:00.5Z"}, "committed_at"),
        ({"root": "SHADOW"}, "root"),
    ],
)
def test_field_rules(overrides, match):
    with pytest.raises(r.ReceiptError, match=match):
        r.build(**_fields(**overrides))


def test_unknown_field_rejected():
    receipt = r.build(**_fields())
    data = receipt.to_dict() | {"signature": "x"}
    with pytest.raises(r.ReceiptError, match="unexpected"):
        r.from_dict(data)


def test_missing_field_rejected():
    data = r.build(**_fields()).to_dict()
    del data["policy_version"]
    with pytest.raises(r.ReceiptError, match="missing"):
        r.from_dict(data)


def test_build_rejects_caller_supplied_digest():
    with pytest.raises(r.ReceiptError, match="unexpected"):
        r.build(**_fields(), receipt_digest="00" * 32)


def test_wrong_profile_or_schema_rejected():
    receipt = r.build(**_fields())
    with pytest.raises(r.ReceiptError, match="canonicalization"):
        replace(receipt, canonicalization="PG001R-JSON-1")
    with pytest.raises(r.ReceiptError, match="schema"):
        r.from_dict(_with(receipt, schema="receipt.v1"))


def test_receipt_is_immutable():
    receipt = r.build(**_fields())
    with pytest.raises(AttributeError):
        receipt.sequence = 5  # type: ignore[misc]


def test_schema_and_contract_agree_on_field_set():
    assert set(SCHEMA["required"]) == set(r.FIELDS)
    assert set(SCHEMA["properties"]) == set(r.FIELDS)
