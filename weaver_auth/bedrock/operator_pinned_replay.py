"""Offline, operator-pinned *local* Chronicle verification candidate.

The pin's SHA-256 MUST arrive through an independent operator-controlled channel.
This program does not authenticate who issued the pin or establish custody,
witness independence, operational execution authority, or E3/E4 evidence.
It does not replace Gate 1's existing test-only receipt contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

MAX_CHRONICLE_BYTES = 1_000_000
MAX_PIN_BYTES = 16_384
HEX = frozenset("0123456789abcdef")


def _is_hex(value: object, size: int) -> bool:
    return isinstance(value, str) and len(value) == size and all(c in HEX for c in value)


def _read_bounded(path: Path, limit: int) -> bytes:
    # Bounded read: do not load an arbitrarily large untrusted file into RAM.
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError("missing, empty or oversized input")
    return raw


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON member")
        obj[key] = value
    return obj


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-JSON constant: {value}")


def _strict_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )


def verify_operator_pin(
    chronicle_path: Path,
    pin_path: Path,
    expected_pin_sha256: str,
    expected_source_commit: str,
) -> dict[str, Any]:
    """Match a local chain to separately supplied pin digest and source SHA.

    A matching locally supplied pin does NOT prove it was issued or retained by
    an independent witness. The caller must establish external pin provenance.
    """
    if not _is_hex(expected_pin_sha256, 64) or not _is_hex(expected_source_commit, 40):
        raise ValueError("invalid or absent externally provided commitment")
    pin_raw = _read_bounded(pin_path, MAX_PIN_BYTES)
    pin_digest = hashlib.sha256(pin_raw).hexdigest()
    if pin_digest != expected_pin_sha256:
        raise ValueError("pin digest differs from externally supplied commitment")
    pin = _strict_json(pin_raw)
    required = {
        "schema_version", "source_commit", "entry_count",
        "terminal_hash", "chronicle_sha256",
    }
    if (
        not isinstance(pin, dict)
        or set(pin) != required
        or type(pin["schema_version"]) is not int
        or pin["schema_version"] != 1
    ):
        raise ValueError("invalid pin schema or version")
    if not _is_hex(pin["source_commit"], 40) or pin["source_commit"] != expected_source_commit:
        raise ValueError("source commit not bound to operator expectation")
    if type(pin["entry_count"]) is not int or not 0 < pin["entry_count"] <= MAX_CHRONICLE_BYTES:
        raise ValueError("invalid entry count")
    if not _is_hex(pin["terminal_hash"], 64) or not _is_hex(pin["chronicle_sha256"], 64):
        raise ValueError("invalid hash commitment")

    raw = _read_bounded(chronicle_path, MAX_CHRONICLE_BYTES)
    input_digest = hashlib.sha256(raw).hexdigest()
    if input_digest != pin["chronicle_sha256"]:
        raise ValueError("chronicle bytes do not match pinned digest")
    lines = raw.decode("utf-8").splitlines()
    if not lines or len(lines) != pin["entry_count"] or any(not line.strip() for line in lines):
        raise ValueError("missing, blank or extra chronicle entries")

    previous = "GENESIS"
    for line in lines:
        entry = _strict_json(line.encode("utf-8"))
        if not isinstance(entry, dict) or entry.get("prev_hash") != previous:
            raise ValueError("invalid entry or broken previous-hash linkage")
        actual = entry.get("entry_hash")
        if not _is_hex(actual, 64):
            raise ValueError("entry hash missing or malformed")
        body = {key: value for key, value in entry.items() if key != "entry_hash"}
        canonical = json.dumps(
            body, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        computed = hashlib.sha256(previous.encode("ascii") + canonical).hexdigest()
        if computed != actual:
            raise ValueError("entry digest mismatch")
        previous = actual
    if previous != pin["terminal_hash"]:
        raise ValueError("terminal chain hash differs from operator-pinned tip")

    return {
        "status": "PIN_MATCH_LOCAL_CHAIN_PASS",
        "scope": "PIN_BOUND_LOCAL_REPLAY_ONLY",
        "source_commit": expected_source_commit,
        "pin_sha256": pin_digest,
        "chronicle_sha256": input_digest,
        "entry_count": len(lines),
        "terminal_hash": previous,
        "independent_pin_custody": "NOT_ESTABLISHED_BY_THIS_TOOL",
        "independent_witness": "NOT_ESTABLISHED",
        "operational_authority": "NONE",
        "evidence_promotion": "NONE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded local replay against operator-supplied pin"
    )
    parser.add_argument("--chronicle", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--expected-pin-sha256", required=True)
    parser.add_argument("--expected-source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_operator_pin(
            args.chronicle, args.pin, args.expected_pin_sha256, args.expected_source_commit,
        )
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        report = {
            "status": "FAILURE",
            "scope": "PIN_BOUND_LOCAL_REPLAY_ONLY",
            "independent_witness": "NOT_ESTABLISHED",
            "operational_authority": "NONE",
            "evidence_promotion": "NONE",
        }
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
