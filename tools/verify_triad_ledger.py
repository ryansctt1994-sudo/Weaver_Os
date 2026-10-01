"""Fail-closed verification of a nonempty signed Triad JSONL ledger."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from triadic_controls.ledger import TriadLedger


def verify_file(path: Path, expected_head: str, trusted_key_sha256: str) -> dict[str, str | int]:
    for name, value in (("head", expected_head), ("key fingerprint", trusted_key_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid expected {name}")

    if not path.is_file():
        raise ValueError("ledger file missing")
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("ledger is empty or has invalid line framing")
    lines = raw.splitlines()
    if any(not line for line in lines):
        raise ValueError("blank ledger line")

    events = TriadLedger(path).load_events()
    if not events or len(events) != len(lines):
        raise ValueError("ledger is empty or has skipped lines")
    for index, event in enumerate(events):
        if not event.get("signature"):
            raise ValueError(f"unsigned event at index {index}")
        try:
            key = bytes.fromhex(event["public_key"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"invalid key at index {index}") from exc
        if hashlib.sha256(key).hexdigest() != trusted_key_sha256:
            raise ValueError(f"untrusted key at index {index}")
    if events[-1]["event_hash"] != expected_head:
        raise ValueError("ledger head mismatch")

    return {
        "events": len(events),
        "head": expected_head,
        "key_sha256": trusted_key_sha256,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--trusted-key-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(verify_file(args.ledger, args.expected_head, args.trusted_key_sha256)))


if __name__ == "__main__":
    main()
