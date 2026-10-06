"""Emit a machine-readable bounded spine receipt.

The receipt records a local or CI execution of the deterministic Weaver spine.
It does not establish independent operator reproduction, witness promotion,
operational authority, or production permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from tools.authority_state import AuthorityStateError, replay_authority_state
from tools.spine_hash import SpineValidationError, canonical, chain_events, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "authority_ledger.json"
MANIFEST_PATH = ROOT / "published_manifest.json"
SCHEMA = "weaver-spine-execution-receipt-1"


class SpineReceiptError(ValueError):
    pass


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SpineReceiptError(f"MISSING_ARTIFACT:{path.name}") from exc
    except json.JSONDecodeError as exc:
        raise SpineReceiptError(f"INVALID_JSON:{path.name}") from exc


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _manifest_hash(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    return sha256_hex(canonical(payload))


def _receipt_hash(receipt: Mapping[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    return hashlib.sha256(canonical(payload)).hexdigest()


def build_receipt(
    manifest: Mapping[str, Any],
    ledger: Any,
    *,
    source_commit: str,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    try:
        ledger_hash, chain_head = chain_events(ledger)
        state_result = replay_authority_state(ledger)
    except (SpineValidationError, AuthorityStateError) as exc:
        raise SpineReceiptError(f"SPINE_REPLAY_INVALID:{exc}") from exc

    checks = {
        "authority_ledger_hash": ledger_hash == manifest.get("authority_ledger_hash"),
        "chain_head": chain_head == manifest.get("expected_head_hash"),
        "local_state_digest": state_result.digest == manifest.get("expected_state_digest"),
        "state_digest_method": state_result.method == manifest.get("state_digest_method"),
        "manifest_hash": _manifest_hash(manifest) == manifest.get("manifest_hash"),
    }
    overall = "PASS" if all(checks.values()) else "FAIL"

    github_actions = environ.get("GITHUB_ACTIONS") == "true"
    execution_class = (
        "REMOTE_CI_SAME_ORIGIN" if github_actions else "LOCAL_OPERATOR_EXECUTION"
    )

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "source_base_commit": manifest.get("source_base_commit"),
        "execution_class": execution_class,
        "operator_independence": "NOT_ESTABLISHED",
        "witness_state": "W0",
        "operational_authority": "O0_WITHHELD",
        "production": "PROHIBITED",
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "runner_os": environ.get("RUNNER_OS", "local"),
            "runner_arch": environ.get("RUNNER_ARCH", "unknown"),
            "github_run_id": environ.get("GITHUB_RUN_ID", "local"),
            "github_run_attempt": environ.get("GITHUB_RUN_ATTEMPT", "local"),
        },
        "derived": {
            "authority_ledger_hash": ledger_hash,
            "chain_head": chain_head,
            "local_state_digest": state_result.digest,
            "state_digest_method": state_result.method,
            "local_state": state_result.state,
        },
        "manifest": {
            "manifest_version": manifest.get("manifest_version"),
            "manifest_hash": manifest.get("manifest_hash"),
            "state_digest_status": manifest.get("state_digest_status"),
            "release_commit": manifest.get("release_commit"),
            "environment_status": manifest.get("environment_status"),
        },
        "checks": checks,
        "overall_result": overall,
        "limitations": [
            "same-origin automated execution is not independent operator reproduction",
            "local reducer state is not Chronicle/Raft runtime state",
            "receipt does not grant authority or production permission",
        ],
    }
    receipt["receipt_sha256"] = _receipt_hash(receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "spine-execution-receipt.json",
    )
    args = parser.parse_args(argv)

    try:
        manifest = _load_json(MANIFEST_PATH)
        ledger = _load_json(LEDGER_PATH)
        if not isinstance(manifest, dict):
            raise SpineReceiptError("MANIFEST_NOT_OBJECT")
        receipt = build_receipt(
            manifest,
            ledger,
            source_commit=os.environ.get("GITHUB_SHA") or _git_head(),
            environ=os.environ,
        )
    except SpineReceiptError as exc:
        print(f"SPINE_RECEIPT_REFUSED:{exc}", file=sys.stderr)
        return 2

    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["overall_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
