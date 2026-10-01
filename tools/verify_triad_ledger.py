"""Fail-closed verification of a nonempty signed Triad JSONL ledger."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from triadic_controls.ledger import verify_chain


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def verify_bytes(
    raw: bytes,
    expected_head: str,
    trusted_key_sha256: str,
    expected_file_sha256: str | None = None,
) -> dict[str, str | int]:
    """Verify and hash the same immutable bytes, without reopening their source."""
    for name, value in (("head", expected_head), ("key fingerprint", trusted_key_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid expected {name}")

    file_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_file_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_file_sha256):
            raise ValueError("invalid expected file digest")
        if file_sha256 != expected_file_sha256:
            raise ValueError("ledger file digest mismatch")

    if not raw or not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("ledger is empty or has invalid line framing")
    lines = raw.split(b"\n")[:-1]
    if any(not line for line in lines):
        raise ValueError("blank ledger line")

    events = []
    for line in lines:
        event = json.loads(
            line.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(event, dict):
            raise ValueError("ledger line is not an object")
        events.append(event)
    events = verify_chain(events)
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
        "file_sha256": file_sha256,
    }


def verify_file(
    path: Path,
    expected_head: str,
    trusted_key_sha256: str,
    expected_file_sha256: str | None = None,
) -> dict[str, str | int]:
    return verify_bytes(path.read_bytes(), expected_head, trusted_key_sha256, expected_file_sha256)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--trusted-key-sha256", required=True)
    parser.add_argument("--expected-file-sha256")
    args = parser.parse_args()
    result = verify_file(
        args.ledger, args.expected_head, args.trusted_key_sha256, args.expected_file_sha256
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
