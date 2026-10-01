"""Three-event byte-tamper and substitution checks for the pinned verifier."""

import hashlib
import json
from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tools.verify_triad_ledger import verify_file
from triadic_controls.ledger import GENESIS_PREV_HASH, compute_event_hash


def signed_chain(key):
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    events = []
    previous = GENESIS_PREV_HASH
    for index in range(3):
        event = {
            "index": index,
            "timestamp": "2026-09-30T00:00:00Z",
            "event_type": "proposal",
            "actor": "test-operator",
            "public_key": public.hex(),
            "payload": {"id": f"event-{index}", "value": index},
            "prev_hash": previous,
            "event_hash": "",
            "policy_version": "test-v1",
        }
        event["event_hash"] = compute_event_hash(event)
        event["signature"] = key.sign(event["event_hash"].encode()).hex()
        events.append(event)
        previous = event["event_hash"]
    return events, hashlib.sha256(public).hexdigest()


def write(path, events):
    path.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events), encoding="utf-8")


def test_three_events_and_middle_byte_tamper(tmp_path):
    events, fingerprint = signed_chain(Ed25519PrivateKey.generate())
    path = tmp_path / "ledger.jsonl"
    write(path, events)
    assert verify_file(path, events[-1]["event_hash"], fingerprint)["events"] == 3

    raw = path.read_bytes()
    path.write_bytes(raw.replace(b"event-1", b"event-X", 1))
    with pytest.raises(ValueError, match="event_hash mismatch"):
        verify_file(path, events[-1]["event_hash"], fingerprint)


def test_truncation_and_fully_resigned_rewrite_fail(tmp_path):
    key = Ed25519PrivateKey.generate()
    events, fingerprint = signed_chain(key)
    path = tmp_path / "ledger.jsonl"
    write(path, events[:-1])
    with pytest.raises(ValueError, match="head mismatch"):
        verify_file(path, events[-1]["event_hash"], fingerprint)

    replacement, _ = signed_chain(Ed25519PrivateKey.generate())
    write(path, replacement)
    with pytest.raises(ValueError, match="untrusted key"):
        verify_file(path, replacement[-1]["event_hash"], fingerprint)


def test_missing_signature_and_blank_line_fail(tmp_path):
    events, fingerprint = signed_chain(Ed25519PrivateKey.generate())
    path = tmp_path / "ledger.jsonl"
    unsigned = deepcopy(events)
    unsigned[1].pop("signature")
    write(path, unsigned)
    with pytest.raises(ValueError, match="unsigned event"):
        verify_file(path, events[-1]["event_hash"], fingerprint)

    write(path, events)
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="blank ledger line"):
        verify_file(path, events[-1]["event_hash"], fingerprint)
