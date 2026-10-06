"""Pure canonical hashing helpers for the Weaver fail-closed spine.

This module contains mechanics only. It does not assign evidence levels,
witness status, authority, or production permission.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

ZERO = "0" * 64


class SpineValidationError(ValueError):
    """Raised when ledger input cannot be admitted to the canonical chain."""


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ordered_events(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list) or not events:
        raise SpineValidationError("ledger must be a non-empty list")
    if not all(isinstance(item, dict) for item in events):
        raise SpineValidationError("every ledger event must be an object")
    return sorted(events, key=lambda item: item.get("sequence_number", 0))


def chain_events(events: Any) -> tuple[str, str]:
    """Return (canonical_ledger_hash, ordered_chain_head).

    The chain commits to predecessor head, sequence number, event type, and
    payload. Sequence numbers must be exactly 1..N.
    """
    ordered = ordered_events(events)
    expected = 1
    head = ZERO

    for event in ordered:
        seq = event.get("sequence_number")
        if seq != expected:
            raise SpineValidationError(
                f"sequence gap: expected {expected}, got {seq}"
            )
        if "event_type" not in event or "payload" not in event:
            raise SpineValidationError(
                f"event {seq} missing event_type or payload"
            )
        block = {
            "prev": head,
            "sequence_number": seq,
            "event_type": event["event_type"],
            "payload": event["payload"],
        }
        head = sha256_hex(canonical(block))
        expected += 1

    ledger_hash = sha256_hex(canonical(ordered))
    return ledger_hash, head
