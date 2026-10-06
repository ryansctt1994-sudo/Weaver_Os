"""Deterministic local reducer for the canonical authority transition ledger.

This module derives a *local reference state projection* from
`authority_ledger.json`. It is not Chronicle/Raft runtime state and must not be
presented as an independently reproduced runtime state digest.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from tools.spine_hash import SpineValidationError, canonical, chain_events, ordered_events

_STATE_DIGEST_METHOD = "authority-transition-reducer-v1"
_ALLOWED_PAYLOAD_FIELDS = {
    "current_state",
    "target_state",
    "receipt_id",
    "signature_hash",
}


class AuthorityStateError(ValueError):
    """Raised when authority-ledger events cannot be reduced deterministically."""


@dataclass(frozen=True)
class AuthorityStateResult:
    state: dict[str, str]
    digest: str
    method: str
    events: int


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityStateError(f"duplicate payload key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AuthorityStateError(f"invalid JSON constant: {value}")


def _parse_payload(raw: Any, sequence_number: int) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise AuthorityStateError(
            f"payload at sequence {sequence_number} must be a JSON string"
        )
    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise AuthorityStateError(
            f"invalid payload JSON at sequence {sequence_number}"
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorityStateError(
            f"payload at sequence {sequence_number} must decode to an object"
        )

    required = {"current_state", "target_state", "receipt_id"}
    missing = sorted(required - set(payload))
    if missing:
        raise AuthorityStateError(
            f"payload at sequence {sequence_number} missing: {','.join(missing)}"
        )
    extra = sorted(set(payload) - _ALLOWED_PAYLOAD_FIELDS)
    if extra:
        raise AuthorityStateError(
            f"payload at sequence {sequence_number} has unrecognized fields: "
            + ",".join(extra)
        )

    for name in required:
        if not isinstance(payload[name], str) or not payload[name]:
            raise AuthorityStateError(
                f"payload field {name} at sequence {sequence_number} must be non-empty"
            )
    if payload["current_state"] == payload["target_state"]:
        raise AuthorityStateError(
            f"no-op transition at sequence {sequence_number}"
        )

    signature_hash = payload.get("signature_hash")
    if signature_hash is not None and (
        not isinstance(signature_hash, str) or not signature_hash
    ):
        raise AuthorityStateError(
            f"signature_hash at sequence {sequence_number} must be non-empty"
        )
    return payload


def replay_authority_state(events: Any) -> AuthorityStateResult:
    """Replay the admitted transition ledger into a small canonical state.

    The projection is intentionally narrow:
      {"receipt_id": <stable receipt identity>, "state": <final target state>}

    The ledger head commits to history; this digest commits only to the final
    projected state. They are separate properties.
    """
    try:
        chain_events(events)
        ordered = ordered_events(events)
    except SpineValidationError as exc:
        raise AuthorityStateError(f"invalid ledger chain: {exc}") from exc

    receipt_id: str | None = None
    current_state: str | None = None

    for event in ordered:
        sequence_number = event["sequence_number"]
        if event["event_type"] != "STATE_TRANSITION":
            raise AuthorityStateError(
                f"unsupported event_type at sequence {sequence_number}: "
                f"{event['event_type']}"
            )

        payload = _parse_payload(event["payload"], sequence_number)

        if receipt_id is None:
            receipt_id = payload["receipt_id"]
            current_state = payload["current_state"]
        else:
            if payload["receipt_id"] != receipt_id:
                raise AuthorityStateError(
                    f"receipt_id changed at sequence {sequence_number}"
                )
            if payload["current_state"] != current_state:
                raise AuthorityStateError(
                    f"state discontinuity at sequence {sequence_number}: "
                    f"expected {current_state}, got {payload['current_state']}"
                )

        current_state = payload["target_state"]

    if receipt_id is None or current_state is None:
        raise AuthorityStateError("ledger produced no authority state")

    state = {"receipt_id": receipt_id, "state": current_state}
    digest = hashlib.sha256(canonical(state)).hexdigest()
    return AuthorityStateResult(
        state=state,
        digest=digest,
        method=_STATE_DIGEST_METHOD,
        events=len(ordered),
    )
