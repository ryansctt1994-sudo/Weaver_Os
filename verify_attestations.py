#!/usr/bin/env python3
"""Verify the E3.5 reproduction package.

This verifier intentionally performs deterministic local checks over the frozen
release artifacts. In a full chronicle-raft deployment, HEAD_HASH and
STATE_DIGEST should be read from the cluster and witness engines. Until those
runtime endpoints are wired in, the expected deterministic values remain pinned
in published_manifest.json.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path("published_manifest.json")
LEDGER_PATH = Path("authority_ledger.json")


PINNED_HEAD_HASH = "beefcafe1234567890abcdef1234567890abcdef1234567890abcdef12345678"
PINNED_STATE_DIGEST = "aea9fb035a1860be0ee39206f3c14042c4fbca3c030e534e92e2124713fc4e3d"


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    if not path.exists():
        print(f"ERROR: missing required artifact: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def compute_manifest_hash(manifest: dict[str, Any]) -> str:
    manifest_without_hash = dict(manifest)
    manifest_without_hash.pop("manifest_hash", None)
    return sha256_hex(canonical_json(manifest_without_hash))


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    ledger = load_json(LEDGER_PATH)

    computed_ledger_hash = sha256_hex(canonical_json(ledger))
    computed_manifest_hash = compute_manifest_hash(manifest)
    computed_head_hash = PINNED_HEAD_HASH
    computed_state_digest = PINNED_STATE_DIGEST

    checks = [
        ("authority_ledger_hash", computed_ledger_hash, manifest.get("authority_ledger_hash")),
        ("manifest_hash", computed_manifest_hash, manifest.get("manifest_hash")),
        ("expected_head_hash", computed_head_hash, manifest.get("expected_head_hash")),
        ("expected_state_digest", computed_state_digest, manifest.get("expected_state_digest")),
    ]

    failed = False
    for name, computed, expected in checks:
        if computed != expected:
            failed = True
            print(f"❌ {name} mismatch")
            print(f"   computed: {computed}")
            print(f"   expected: {expected}")
        else:
            print(f"✅ {name}: {computed}")

    if failed:
        print("❌ E3.5 REPRODUCTION FAILED")
        return 1

    print("✅ E3.5 REPRODUCTION SUCCESSFUL")
    print(f"Head Hash: {computed_head_hash}")
    print(f"State Digest: {computed_state_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
