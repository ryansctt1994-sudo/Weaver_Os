#!/usr/bin/env python3
"""Negative control helper for RECEIPT_BINDING_GATE_v1.

This command intentionally uses inverted CI semantics because bind_receipt()
expects the negative-control command to FAIL when a known forgery is correctly
rejected.

Exit code:
    1 when the forged receipt is rejected as expected
    0 when the forged receipt unexpectedly matches the artifact tree
    2 for malformed inputs/errors
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt_binding import sha256_file  # noqa: E402


def _safe_join(root: str, rel: str) -> str:
    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, rel))
    if os.path.commonpath([root_real, candidate]) != root_real:
        raise ValueError(f"path escapes artifact root: {rel!r}")
    return candidate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reject a known forged receipt")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--artifact-root", required=True)
    args = parser.parse_args(argv)

    try:
        with open(args.receipt, encoding="utf-8") as f:
            receipt = json.load(f)
        declared = receipt["hashes"]
        if not isinstance(declared, dict) or not declared:
            print("[negative-control] malformed forged receipt: no hashes", file=sys.stderr)
            return 2

        artifact_root = os.path.realpath(args.artifact_root)
        bad = 0
        for rel, expected in declared.items():
            path = _safe_join(artifact_root, rel)
            actual = sha256_file(path) if os.path.isfile(path) else None
            if actual != expected:
                bad += 1
                print(f"[negative-control] rejected forged hash for {rel}")

        if bad:
            print(f"[negative-control] forged receipt rejected as expected ({bad} mismatch(es))")
            return 1

        print("[negative-control] forged receipt unexpectedly matched; rejection path unproven")
        return 0
    except Exception as exc:
        print(f"[negative-control] error: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
