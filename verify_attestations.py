#!/usr/bin/env python3
"""Bounded verifier for the Weaver fail-closed spine.

Scopes:
- local-spine: derive ledger hash, ordered chain head, and the bounded local
  authority-state projection from ledger bytes; validate manifest schema and
  compare derived values to the manifest.
- e35: run the local checks, then fail closed while released-artifact replay,
  runtime-derived state, and independent reproduction remain unimplemented.

A local-spine pass is not E3.5, witness, authority, or production permission.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker

from tools.authority_state import AuthorityStateError, replay_authority_state
from tools.spine_hash import SpineValidationError, canonical, chain_events, sha256_hex

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "published_manifest.json"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "published_manifest.schema.json"
LEDGER_PATH = ROOT / "authority_ledger.json"


class VerificationError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys at every nesting level, before schema evaluation."""
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"DUPLICATE_KEY:{key}")
        obj[key] = value
    return obj


def _reject_nonfinite(token: str) -> Any:
    """Python JSON accepts non-standard NaN/Infinity by default; refuse them."""
    raise ValueError(f"NONFINITE_JSON_CONSTANT:{token}")


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ValueError(f"NONFINITE_JSON_NUMBER:{token}")
    return value


def load_json(path: Path) -> Any:
    if not path.exists():
        raise VerificationError(f"MISSING_ARTIFACT:{path.name}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
            parse_float=_finite_float,
        )
    except (ValueError, UnicodeError) as exc:
        raise VerificationError(f"INVALID_JSON:{path.name}:{exc}") from exc


def compute_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    return sha256_hex(canonical(payload))


def require_manifest_v12(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise VerificationError("MANIFEST_NOT_OBJECT")

    schema = load_json(MANIFEST_SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise VerificationError("MANIFEST_SCHEMA_NOT_OBJECT")

    try:
        Draft7Validator.check_schema(schema)
    except Exception as exc:
        raise VerificationError(f"MANIFEST_SCHEMA_INVALID:{exc}") from exc

    validator = Draft7Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(manifest),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise VerificationError(
            f"MANIFEST_SCHEMA_REJECTED:{location}:{first.message}"
        )

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
        authority_state = replay_authority_state(ledger)
    except (SpineValidationError, AuthorityStateError) as exc:
        raise VerificationError(f"LEDGER_REPLAY_INVALID:{exc}") from exc

    checks = [
        compare(
            "authority_ledger_hash",
            ledger_hash,
            manifest.get("authority_ledger_hash"),
        ),
        compare(
            "manifest_hash",
            compute_manifest_hash(manifest),
            manifest.get("manifest_hash"),
        ),
        compare(
            "expected_head_hash",
            chain_head,
            manifest.get("expected_head_hash"),
        ),
        compare(
            "expected_state_digest",
            authority_state.digest,
            manifest.get("expected_state_digest"),
        ),
        compare(
            "state_digest_method",
            authority_state.method,
            manifest.get("state_digest_method"),
        ),
    ]
    print(f"derived_chain_head: {chain_head}")
    print(f"derived_local_state_digest: {authority_state.digest}")
    print(
        "derived_local_state: "
        + json.dumps(authority_state.state, sort_keys=True, separators=(",", ":"))
    )
    return all(checks)


def verify_e35_prerequisites(manifest: dict[str, Any]) -> bool:
    ok = True

    if manifest.get("release_commit") is None:
        print("FAIL release_commit: UNBOUND")
        ok = False

    if manifest.get("environment_status") != "REPLAYED":
        print(f"FAIL environment_status: {manifest.get('environment_status')}")
        ok = False

    if manifest.get("state_digest_status") != "COMPUTED_FROM_RUNTIME":
        print(
            "FAIL state_digest_status: "
            + str(manifest.get("state_digest_status"))
            + " (runtime replay required)"
        )
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
        manifest = require_manifest_v12(load_json(MANIFEST_PATH))
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
        print("STATE_DIGEST_CLASS: LOCAL_REDUCER_COMPUTED")
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
