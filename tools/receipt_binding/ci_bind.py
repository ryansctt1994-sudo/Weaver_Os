#!/usr/bin/env python3
"""ci_bind.py — thin CI wrapper around RECEIPT_BINDING_GATE_v1.

It owns no hash/replay/negative-control logic. It reads a receipt plus a small
binding manifest, then delegates entirely to receipt_binding.bind_receipt().

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
from receipt_binding import bind_receipt  # noqa: E402


def _resolve(base: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CI wrapper for RECEIPT_BINDING_GATE_v1")
    parser.add_argument(
        "--manifest",
        required=True,
        help="JSON: {receipt_path, artifact_root, replay_command, negative_control_command}",
    )
    args = parser.parse_args(argv)

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)

    base = os.path.dirname(os.path.abspath(args.manifest))
    receipt_path = _resolve(base, manifest["receipt_path"])
    artifact_root = _resolve(base, manifest["artifact_root"])

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
