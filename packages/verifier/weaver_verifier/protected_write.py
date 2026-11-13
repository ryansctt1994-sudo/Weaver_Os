"""Read-only replay of WEAVER-VERTICAL-001 SQLite effects.

No operational authority: this reconstructs state from a verified local history.
A separate, externally retained anchor is required to detect whole-history rewrites.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from weaver_contracts.canonical import parse_strict

from .ledger import verify_snapshot


@dataclass(frozen=True)
class ProtectedWriteVerdict:
    ok: bool
    reason: str
    reconstructed: dict[str, str] | None = None
    anchored: bool = False


def verify_protected_write(
    snapshot: Any,
    observed_rows: dict[str, str],
    *,
    anchor: Any = None,
) -> ProtectedWriteVerdict:
    chain = verify_snapshot(snapshot, anchor=anchor)
    if not chain.ok:
        return ProtectedWriteVerdict(False, f"CHAIN_INVALID: {chain.reason}")
    expected: dict[str, str] = {}
    seen: set[str] = set()
    try:
        for entry in snapshot["roots"]["AUTHORITY"]:
            receipt = entry["receipt"]
            if receipt["event_type"] != "EXECUTION_COMMITTED":
                return ProtectedWriteVerdict(False, "UNEXPECTED_AUTHORITY_EVENT")
            event = parse_strict(entry["event"].encode("utf-8"))
            proposal = event["proposal"]
            result = event["result"]
            pid = proposal["proposal_id"]
            payload = proposal["payload"]
            if (
                pid in seen
                or proposal["action"] != "WRITE_KEY"
                or set(payload) != {"key", "value"}
                or result != {
                    "effect": "WRITE_KEY",
                    "key": payload["key"],
                    "value": payload["value"],
                }
                or not isinstance(payload["key"], str)
                or not isinstance(payload["value"], str)
            ):
                return ProtectedWriteVerdict(False, "INVALID_EFFECT_BINDING")
            seen.add(pid)
            expected[payload["key"]] = payload["value"]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return ProtectedWriteVerdict(False, f"REPLAY_INVALID: {type(exc).__name__}")
    if expected != observed_rows:
        return ProtectedWriteVerdict(False, "STATE_MISMATCH", expected, chain.anchored)
    return ProtectedWriteVerdict(True, "STATE_MATCH", expected, chain.anchored)
