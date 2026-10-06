#!/usr/bin/env python3
"""Local fail-closed spine for Weaver_Os.

Evidence ceiling: LOCAL_DETERMINISTIC_CHECK
Authority weight: 0

This is not independent reproduction, not an E3.5 witness, and not operational
authority. It only proves that a local operator can:

1. Canonical-hash authority_ledger.json.
2. Build a hash chain over ordered events.
3. Reject a specified tampered copy as the same state.
4. Optionally report whether the published manifest ledger hash matches.

Run from the repository root:

    python3 tools/fail_closed_spine.py
    python3 tools/fail_closed_spine.py --tamper
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools.spine_hash import SpineValidationError, chain_events
except ModuleNotFoundError:
    # Direct script execution places tools/ rather than the repository root
    # first on sys.path. Import the sibling module without mutating sys.path.
    from spine_hash import SpineValidationError, chain_events

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "authority_ledger.json"
MANIFEST_PATH = ROOT / "published_manifest.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        print(f"FAIL missing artifact: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def tamper(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mutated = copy.deepcopy(events)
    payload = mutated[-1]["payload"]
    mutated[-1]["payload"] = payload + "\nTAMPER"
    return mutated


def derive(events: Any) -> tuple[str, str]:
    try:
        return chain_events(events)
    except SpineValidationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Local fail-closed ledger spine")
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Mutate the last event and require the chain to diverge",
    )
    args = parser.parse_args()

    events = load_json(LEDGER_PATH)
    clean_ledger_hash, clean_head = derive(events)

    print("EVIDENCE_CEILING: LOCAL_DETERMINISTIC_CHECK")
    print("AUTHORITY: O0")
    print(f"events: {len(events)}")
    print(f"ledger_hash: {clean_ledger_hash}")
    print(f"chain_head:  {clean_head}")

    if MANIFEST_PATH.exists():
        manifest = load_json(MANIFEST_PATH)
        published_ledger = manifest.get("authority_ledger_hash")
        published_head = manifest.get("expected_head_hash")

        print(
            "MANIFEST_LEDGER_HASH: "
            + ("MATCH" if published_ledger == clean_ledger_hash else "MISMATCH")
        )
        print(
            "MANIFEST_CHAIN_HEAD: "
            + ("MATCH" if published_head == clean_head else "MISMATCH")
        )

    if not args.tamper:
        print("RESULT: CLEAN_CHAIN_OK")
        return 0

    bad_hash, bad_head = derive(tamper(events))
    if bad_head == clean_head or bad_hash == clean_ledger_hash:
        print("FAIL tamper did not change the chain", file=sys.stderr)
        return 1

    print("TAMPER_LEDGER_HASH: " + bad_hash)
    print("TAMPER_CHAIN_HEAD:  " + bad_head)
    print("RESULT: TAMPER_REJECTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
