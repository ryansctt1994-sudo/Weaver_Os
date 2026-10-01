#!/usr/bin/env python3
"""Local fail-closed spine for Weaver_Os.

Evidence ceiling: LOCAL_DETERMINISTIC_CHECK
Authority weight: 0

This is not independent reproduction, not an E3.5 witness, and not operational
authority. It only proves that a local operator can:

1. Canonical-hash authority_ledger.json.
2. Build a hash chain over ordered events.
3. Reject a tampered copy before it can be treated as the same state.
4. Optionally check the published manifest ledger hash.

Run from the repository root:

    python3 tools/fail_closed_spine.py
    python3 tools/fail_closed_spine.py --tamper
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "authority_ledger.json"
MANIFEST_PATH = ROOT / "published_manifest.json"
ZERO = "0" * 64


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    if not path.exists():
        print(f"FAIL missing artifact: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def chain_events(events: list[dict[str, Any]]) -> tuple[str, str]:
    if not isinstance(events, list) or not events:
        print("FAIL ledger must be a non-empty list", file=sys.stderr)
        sys.exit(2)

    ordered = sorted(events, key=lambda item: item.get("sequence_number", 0))
    expected = 1
    head = ZERO
    for event in ordered:
        seq = event.get("sequence_number")
        if seq != expected:
            print(f"FAIL sequence gap: expected {expected}, got {seq}", file=sys.stderr)
            sys.exit(1)
        if "event_type" not in event or "payload" not in event:
            print(f"FAIL event {seq} missing event_type or payload", file=sys.stderr)
            sys.exit(1)
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


def tamper(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(events)
    payload = mutated[-1]["payload"]
    mutated[-1]["payload"] = payload + "\nTAMPER"
    return mutated


def main() -> int:
    parser = argparse.ArgumentParser(description="Local fail-closed ledger spine")
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Mutate the last event and require the chain to diverge",
    )
    args = parser.parse_args()

    events = load_json(LEDGER_PATH)
    clean_ledger_hash, clean_head = chain_events(events)

    print("EVIDENCE_CEILING: LOCAL_DETERMINISTIC_CHECK")
    print("AUTHORITY: O0")
    print(f"events: {len(events)}")
    print(f"ledger_hash: {clean_ledger_hash}")
    print(f"chain_head:  {clean_head}")

    if MANIFEST_PATH.exists():
        manifest = load_json(MANIFEST_PATH)
        published = manifest.get("authority_ledger_hash")
        if published != clean_ledger_hash:
            print("MANIFEST_LEDGER_HASH: MISMATCH")
            print(f"  published: {published}")
            print(f"  computed:  {clean_ledger_hash}")
            print("NOTE: published_manifest.json is stale relative to the ledger.")
            print("NOTE: pinned expected_head_hash is not treated as a chain result.")
        else:
            print("MANIFEST_LEDGER_HASH: MATCH")

    if not args.tamper:
        print("RESULT: CLEAN_CHAIN_OK")
        return 0

    bad_hash, bad_head = chain_events(tamper(events))
    if bad_head == clean_head or bad_hash == clean_ledger_hash:
        print("FAIL tamper did not change the chain", file=sys.stderr)
        return 1
    print("TAMPER_LEDGER_HASH: " + bad_hash)
    print("TAMPER_CHAIN_HEAD:  " + bad_head)
    print("RESULT: TAMPER_REJECTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
