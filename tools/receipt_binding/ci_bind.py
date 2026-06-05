#!/usr/bin/env python3
"""ci_bind.py — thin CI wrapper around RECEIPT_BINDING_GATE_v1.

It owns no hash/replay/negative-control decision logic. It reads a binding
manifest, optionally builds a receipt from declared hash targets, then delegates
entirely to receipt_binding.bind_receipt().

Exit code:
    0 only if status == VERIFIED
    non-zero otherwise

Usage:
    python tools/receipt_binding/ci_bind.py --manifest path/to/binding_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt_binding import bind_receipt, sha256_file  # noqa: E402


def _resolve(base: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def _safe_target(root: str, rel: str) -> str:
    if os.path.isabs(rel):
        raise ValueError(f"hash target must be relative to artifact_root: {rel!r}")
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, rel))
    if os.path.commonpath([root_real, candidate]) != root_real:
        raise ValueError(f"hash target escapes artifact_root: {rel!r}")
    if not os.path.isfile(candidate):
        raise FileNotFoundError(f"hash target not found: {rel}")
    return candidate


def _build_receipt_from_targets(manifest: dict, artifact_root: str) -> dict:
    targets = manifest.get("hash_targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("hash_targets must be a non-empty list when used")

    hashes = {}
    for rel in targets:
        path = _safe_target(artifact_root, rel)
        hashes[rel] = sha256_file(path)

    return {
        "source": manifest.get("source", "?"),
        "status": manifest.get("status", "DRAFT"),
        "hashes": hashes,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CI wrapper for RECEIPT_BINDING_GATE_v1")
    parser.add_argument(
        "--manifest",
        required=True,
        help="JSON binding manifest. Use receipt_path or hash_targets.",
    )
    args = parser.parse_args(argv)

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)

    base = os.path.dirname(os.path.abspath(args.manifest))
    artifact_root = _resolve(base, manifest["artifact_root"])

    if "hash_targets" in manifest:
        receipt = _build_receipt_from_targets(manifest, artifact_root)
    else:
        receipt_path = _resolve(base, manifest["receipt_path"])
        with open(receipt_path, encoding="utf-8") as f:
            receipt = json.load(f)

    result = bind_receipt(
        receipt=receipt,
        artifact_root=artifact_root,
        replay_command=manifest["replay_command"],
        negative_control_command=manifest["negative_control_command"],
    )

    print(f"[receipt-binding] source={manifest.get('source', '?')} status={result.status.value}")
    if result.reason:
        print(f"[receipt-binding] reason: {result.reason}")
    if result.hash_diffs:
        for rel, diff in result.hash_diffs.items():
            print(
                "[receipt-binding]   "
                f"hash diff {rel}: declared={diff['declared']} actual={diff['actual']}"
            )
    print(
        "[receipt-binding] "
        f"replay_rc={result.replay_returncode} "
        f"negctrl_rc={result.negative_control_returncode}"
    )

    claimed = str(receipt.get("status", "")).upper()
    if claimed == "VERIFIED" and not result.verified:
        print(
            "[receipt-binding] FAIL: receipt claims VERIFIED but gate did not verify it",
            file=sys.stderr,
        )
        return 3

    return 0 if result.verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
