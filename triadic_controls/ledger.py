"""Triad ledger primitives.

This module implements the bounded Triad event-ledger contract used by the
schema track. It validates persisted events against ``schemas/triad_event``;
recomputes event hashes from canonical JSON; verifies optional Ed25519
signatures over ``event_hash``; and verifies append-only chain continuity.

Boundary: this module verifies local ledger integrity. It does not establish
human legitimacy, distributed consensus, production safety, or policy wisdom.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


GENESIS_PREV_HASH = "genesis"
DEFAULT_EVENT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "triad_event.schema.json"


class LedgerValidationError(ValueError):
    """Raised when an event fails schema, hash, signature, or chain validation."""


class LedgerChainError(LedgerValidationError):
    """Raised when ledger ordering or prior-hash continuity fails."""


def canonical_json(data: dict[str, Any]) -> bytes:
    """Return canonical JSON bytes used for Triad hashing.

    The encoding is stable across ordinary Python dict construction order:
    keys are sorted, insignificant whitespace is removed, and NaN/Infinity are
    forbidden.
    """

    return json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def hash_body(event: dict[str, Any]) -> bytes:
    """Canonical event body bytes excluding ``event_hash`` and ``signature``."""

    body = dict(event)
    body.pop("event_hash", None)
    body.pop("signature", None)
    return canonical_json(body)


def compute_event_hash(event: dict[str, Any]) -> str:
    """Compute the Triad event hash for an event-like mapping."""

    return hashlib.sha256(hash_body(event)).hexdigest()


def load_json_schema(path: Path = DEFAULT_EVENT_SCHEMA_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_event_validator(schema_path: Path = DEFAULT_EVENT_SCHEMA_PATH) -> Draft202012Validator:
    schema = load_json_schema(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_event_schema(event: dict[str, Any], validator: Draft202012Validator | None = None) -> None:
    """Validate an event against the Triad event JSON Schema."""

    active_validator = validator or build_event_validator()
    try:
        active_validator.validate(event)
    except ValidationError as exc:
        raise LedgerValidationError(f"event schema validation failed: {exc.message}") from exc


def verify_event_hash(event: dict[str, Any]) -> None:
    """Recompute and verify the stored ``event_hash``."""

    expected_hash = compute_event_hash(event)
    claimed_hash = event.get("event_hash")
    if claimed_hash != expected_hash:
        raise LedgerValidationError(
            f"event_hash mismatch: claimed={claimed_hash!r} expected={expected_hash!r}"
        )


def verify_event_signature(event: dict[str, Any]) -> None:
    """Verify an optional hex Ed25519 signature over ``event_hash``.

    Unsigned events are allowed by the v1.0 schema. If ``signature`` is present,
    it must verify against the hex-encoded Ed25519 public key and the UTF-8
    bytes of the event hash.
    """

    signature_hex = event.get("signature")
    if not signature_hex:
        return

    try:
        public_key_bytes = bytes.fromhex(event["public_key"])
        signature_bytes = bytes.fromhex(signature_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, event["event_hash"].encode("utf-8"))
    except (KeyError, ValueError, TypeError, InvalidSignature) as exc:
        raise LedgerValidationError("event signature verification failed") from exc


def validate_event_integrity(event: dict[str, Any], validator: Draft202012Validator | None = None) -> None:
    """Validate schema, hash binding, and optional signature binding."""

    validate_event_schema(event, validator=validator)
    verify_event_hash(event)
    verify_event_signature(event)


def verify_chain(events: Iterable[dict[str, Any]], validator: Draft202012Validator | None = None) -> list[dict[str, Any]]:
    """Validate an event sequence and return it as a list.

    The chain fails closed when an event index is out of sequence, the genesis
    prior hash is wrong, a prior hash does not match the previous event hash,
    an event hash has been mutated, or a present signature is invalid.
    """

    verified_events = list(events)
    active_validator = validator or build_event_validator()
    previous_hash = GENESIS_PREV_HASH

    for expected_index, event in enumerate(verified_events):
        validate_event_integrity(event, validator=active_validator)

        if event["index"] != expected_index:
            raise LedgerChainError(
                f"event index mismatch at position {expected_index}: got {event['index']}"
            )
        if event["prev_hash"] != previous_hash:
            raise LedgerChainError(
                f"prev_hash mismatch at index {expected_index}: claimed={event['prev_hash']!r} expected={previous_hash!r}"
            )
        previous_hash = event["event_hash"]

    return verified_events


class TriadLedger:
    """JSONL-backed append-only Triad event ledger."""

    def __init__(self, path: str | Path, schema_path: Path = DEFAULT_EVENT_SCHEMA_PATH):
        self.path = Path(path)
        self.validator = build_event_validator(schema_path)

    def load_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise LedgerValidationError(f"invalid JSON on ledger line {line_number}") from exc
                if not isinstance(event, dict):
                    raise LedgerValidationError(f"ledger line {line_number} is not an object")
                events.append(event)

        return verify_chain(events, validator=self.validator)

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        events = self.load_events()
        expected_index = len(events)
        expected_prev_hash = events[-1]["event_hash"] if events else GENESIS_PREV_HASH

        if event.get("index") != expected_index:
            raise LedgerChainError(
                f"event index mismatch: got {event.get('index')!r} expected {expected_index!r}"
            )
        if event.get("prev_hash") != expected_prev_hash:
            raise LedgerChainError(
                f"prev_hash mismatch: got {event.get('prev_hash')!r} expected {expected_prev_hash!r}"
            )

        validate_event_integrity(event, validator=self.validator)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

        return event
