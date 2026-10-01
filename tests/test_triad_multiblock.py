"""Three-event byte-tamper and substitution checks for the pinned verifier."""

import hashlib
import json
from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tools.verify_triad_ledger import verify_bytes, verify_file
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


def encode(events):
    return "".join(json.dumps(e, sort_keys=True) + "\n" for e in events).encode()


def test_file_replacement_cannot_verify_different_bytes(tmp_path, monkeypatch):
    events, fingerprint = signed_chain(Ed25519PrivateKey.generate())
    valid = encode(events)
    tampered = valid.replace(b"event-1", b"event-X", 1)
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(tampered)
    original_read = Path.read_bytes
    reads = []

    def replace_after_read(source):
        captured = original_read(source)
        reads.append(source)
        source.write_bytes(valid)
        return captured

    monkeypatch.setattr(Path, "read_bytes", replace_after_read)
    with pytest.raises(ValueError, match="event_hash mismatch"):
        verify_file(path, events[-1]["event_hash"], fingerprint)
    assert reads == [path]


def test_duplicate_json_field_fails_even_with_valid_final_value():
    events, fingerprint = signed_chain(Ed25519PrivateKey.generate())
    raw = encode(events).replace(b'{"actor":', b'{"actor": "substituted", "actor":', 1)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        verify_bytes(raw, events[-1]["event_hash"], fingerprint)


def test_exact_byte_pin_rejects_unsigned_formatting_change():
    events, fingerprint = signed_chain(Ed25519PrivateKey.generate())
    original = encode(events)
    changed = original.replace(b'"actor": ', b'"actor":  ', 1)
    head = events[-1]["event_hash"]
    digest = hashlib.sha256(original).hexdigest()
    assert verify_bytes(original, head, fingerprint, digest)["events"] == 3
    assert verify_bytes(changed, head, fingerprint)["events"] == 3
    with pytest.raises(ValueError, match="file digest mismatch"):
        verify_bytes(changed, head, fingerprint, digest)


@pytest.mark.parametrize("flags", list(product((False, True), repeat=5)))
def test_bounded_model_verification_predicate(flags):
    """Exercise WitnessBoundary.Verify's 32 Boolean cases on signed JSONL."""
    tampered = flags[:3]
    trusted_key, pinned_head = flags[3:]
    key = Ed25519PrivateKey.generate()
    events, fingerprint = signed_chain(key)
    if not trusted_key:
        events, _ = signed_chain(Ed25519PrivateKey.generate())
    head = events[-1]["event_hash"] if pinned_head else "0" * 64
    raw = encode(events)
    for index, changed in enumerate(tampered):
        if changed:
            raw = raw.replace(f"event-{index}".encode(), f"other-{index}".encode(), 1)
    expected = not any(tampered) and trusted_key and pinned_head
    if expected:
        result = verify_bytes(raw, head, fingerprint)
        assert result["file_sha256"] == hashlib.sha256(raw).hexdigest()
        assert result["events"] == 3
    else:
        with pytest.raises(ValueError):
            verify_bytes(raw, head, fingerprint)
