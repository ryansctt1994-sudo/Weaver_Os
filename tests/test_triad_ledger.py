from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from triadic_controls.ledger import (
    GENESIS_PREV_HASH,
    LedgerChainError,
    LedgerValidationError,
    TriadLedger,
    compute_event_hash,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture
def signing_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
def public_key_hex(signing_key: Ed25519PrivateKey) -> str:
    return signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def build_event(
    *,
    index: int,
    prev_hash: str,
    public_key_hex: str,
    signing_key: Ed25519PrivateKey | None = None,
    event_type: str = "proposal",
    payload: dict | None = None,
    policy_version: str = "policy-v1",
) -> dict:
    event = {
        "index": index,
        "timestamp": utc_now(),
        "event_type": event_type,
        "actor": "user123",
        "public_key": public_key_hex,
        "payload": payload or {
            "id": f"p{index}",
            "action": "update_config",
            "value": 0.8,
        },
        "prev_hash": prev_hash,
        "event_hash": "",
        "policy_version": policy_version,
    }
    event["event_hash"] = compute_event_hash(event)
    if signing_key is not None:
        event["signature"] = signing_key.sign(event["event_hash"].encode("utf-8")).hex()
    return event


def test_append_and_load_valid_signed_event(tmp_path, signing_key, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(
        index=0,
        prev_hash=GENESIS_PREV_HASH,
        public_key_hex=public_key_hex,
        signing_key=signing_key,
    )

    ledger.append_event(event)

    assert ledger.load_events() == [event]


def test_append_rejects_missing_policy_version(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(index=0, prev_hash=GENESIS_PREV_HASH, public_key_hex=public_key_hex)
    event.pop("policy_version")

    with pytest.raises(LedgerValidationError, match="schema validation failed"):
        ledger.append_event(event)


def test_append_rejects_invalid_event_type(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(
        index=0,
        prev_hash=GENESIS_PREV_HASH,
        public_key_hex=public_key_hex,
        event_type="authorized_without_replay",
    )

    with pytest.raises(LedgerValidationError, match="schema validation failed"):
        ledger.append_event(event)


def test_append_rejects_mutated_hash_body(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(index=0, prev_hash=GENESIS_PREV_HASH, public_key_hex=public_key_hex)
    event["payload"]["value"] = 0.9

    with pytest.raises(LedgerValidationError, match="event_hash mismatch"):
        ledger.append_event(event)


def test_append_rejects_broken_chain_continuity(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(index=0, prev_hash="not-genesis", public_key_hex=public_key_hex)

    with pytest.raises(LedgerChainError, match="prev_hash mismatch"):
        ledger.append_event(event)


def test_append_rejects_invalid_signature(tmp_path, signing_key, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(
        index=0,
        prev_hash=GENESIS_PREV_HASH,
        public_key_hex=public_key_hex,
        signing_key=signing_key,
    )
    event["signature"] = "00" * 64

    with pytest.raises(LedgerValidationError, match="signature verification failed"):
        ledger.append_event(event)


def test_load_rejects_tampered_persisted_event(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    event = build_event(index=0, prev_hash=GENESIS_PREV_HASH, public_key_hex=public_key_hex)
    ledger.append_event(event)

    tampered = deepcopy(event)
    tampered["payload"]["value"] = 1.0
    ledger.path.write_text(f"{tampered}\n".replace("'", '"'), encoding="utf-8")

    with pytest.raises(LedgerValidationError, match="event_hash mismatch"):
        ledger.load_events()


def test_append_second_event_requires_previous_hash(tmp_path, public_key_hex):
    ledger = TriadLedger(tmp_path / "triad.jsonl")
    first = build_event(index=0, prev_hash=GENESIS_PREV_HASH, public_key_hex=public_key_hex)
    ledger.append_event(first)

    second = build_event(index=1, prev_hash="wrong", public_key_hex=public_key_hex)

    with pytest.raises(LedgerChainError, match="prev_hash mismatch"):
        ledger.append_event(second)
