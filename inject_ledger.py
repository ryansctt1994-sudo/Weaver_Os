#!/usr/bin/env python3
"""Inject authority ledger events into a chronicle-raft leader.

Usage:
    python3 inject_ledger.py authority_ledger.json

By default this targets http://localhost:8080/events. Override with:
    CHRONICLE_EVENTS_URL=http://host:port/events python3 inject_ledger.py authority_ledger.json
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_EVENTS_URL = "http://localhost:8080/events"


def post_json(url: str, payload: dict) -> None:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError(f"unexpected HTTP status {response.status}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 inject_ledger.py authority_ledger.json", file=sys.stderr)
        return 2

    ledger_path = Path(sys.argv[1])
    if not ledger_path.exists():
        print(f"ERROR: missing ledger file: {ledger_path}", file=sys.stderr)
        return 2

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    events_url = os.environ.get("CHRONICLE_EVENTS_URL", DEFAULT_EVENTS_URL)

    for event in ledger:
        try:
            post_json(events_url, event)
            print(f"injected sequence_number={event.get('sequence_number')}")
        except (urllib.error.URLError, RuntimeError) as exc:
            print(f"ERROR: failed to inject event {event.get('sequence_number')}: {exc}", file=sys.stderr)
            return 1

    print("ledger injection complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
