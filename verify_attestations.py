#!/usr/bin/env python3
"""Bounded verifier for the Weaver fail-closed spine.

Scopes:
- local-spine: derive ledger hash and ordered chain head from ledger bytes,
  recompute manifest hash, and compare those values to the manifest.
- e35: run the local checks, then fail closed while runtime replay and
  independent reproduction gates remain unimplemented.

A local-spine pass is not E3.5, witness, authority, or production permission.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.spine_hash import SpineValidationError, canonical, chain_events, sha256_hex

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "published_manifest.json"
LEDGER_PATH = ROOT / "authority_ledger.json"


class VerificationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    if not path.exists():
        raise VerificationError(f"MISSING_ARTIFACT:{path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"INVALID_JSON:{path.name}:{exc.msg}") from exc


def compute_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    return sha256_hex(canonical(payload))


def require_manifest_v11(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise VerificationError("MANIFEST_NOT_OBJECT")

    required = {
        "manifest_version",
        "source_base_commit",
        "release_commit",
        "docker_image",
        "environment",
        "environment_status",
        "authority_ledger_hash",
        "expected_head_hash",
        "expected_state_digest",
        "state_digest_status",
        "timestamp",
        "manifest_hash",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise VerificationError("MANIFEST_FIELDS_MISSING:" + ",".join(missing))
    if manifest.get("manifest_version") != "1.1":
        raise VerificationError("MANIFEST_VERSION_UNSUPPORTED")
    return manifest


def compare(name: str, computed: Any, expected: Any) -> bool:
    ok = computed == expected
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        print(f"  computed: {computed}")
        print(f"  expected: {expected}")
    return ok


def verify_local_spine(manifest: dict[str, Any], ledger: Any) -> bool:
    try:
        ledger_hash, chain_head = chain_events(ledger)
    except SpineValidationError as exc:
        raise VerificationError(f"LEDGER_INVALID:{exc}") from exc

    checks = [
        compare("authority_ledger_hash", ledger_hash, manifest.get("authority_ledger_hash")),
        compare("manifest_hash", compute_manifest_hash(manifest), manifest.get("manifest_hash")),
        compare("expected_head_hash", chain_head, manifest.get("expected_head_hash")),
    ]
    print(f"derived_chain_head: {chain_head}")
    return all(checks)


def verify_e35_prerequisites(manifest: dict[str, Any]) -> bool:
    ok = True

    if manifest.get("release_commit") is None:
        print("FAIL release_commit: UNBOUND")
        ok = False

    if manifest.get("environment_status") != "REPLAYED":
        print(f"FAIL environment_status: {manifest.get('environment_status')}")
        ok = False

    if (
        manifest.get("state_digest_status") != "COMPUTED_FROM_RUNTIME"
        or manifest.get("expected_state_digest") is None
    ):
        print("FAIL state_digest: NOT_COMPUTED_FROM_RUNTIME")
        ok = False
    else:
        print("FAIL state_digest: RUNTIME_REPLAY_INPUT_NOT_IMPLEMENTED")
        ok = False

    print("FAIL independent_reproduction: NOT_IMPLEMENTED_BY_LOCAL_VERIFIER")
    ok = False
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        choices=("local-spine", "e35"),
        default="e35",
        help="Qualification scope. Default remains strict E3.5.",
    )
    args = parser.parse_args(argv)

    try:
        manifest = require_manifest_v11(load_json(MANIFEST_PATH))
        ledger = load_json(LEDGER_PATH)
        local_ok = verify_local_spine(manifest, ledger)
    except VerificationError as exc:
        print(f"REFUSED {exc}", file=sys.stderr)
        return 2

    if not local_ok:
        print("RESULT: LOCAL_SPINE_FAILED")
        return 1

    if args.scope == "local-spine":
        print("EVIDENCE_CEILING: LOCAL_DETERMINISTIC_CHECK")
        print("AUTHORITY: O0")
        print("RESULT: LOCAL_SPINE_VERIFIED")
        return 0

    if not verify_e35_prerequisites(manifest):
        print("RESULT: E3.5_WITHHELD")
        return 1

    print("RESULT: E3.5_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
