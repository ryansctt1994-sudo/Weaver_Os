#!/usr/bin/env python3
"""Generate a Gate 1 execution receipt for the Weaver Python verification spine.

This script executes the existing test suite, captures stdout/stderr into logs,
hashes those logs, emits a source manifest, and writes a receipt that explicitly
preserves authority_earned=false and production_allowed=false.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SOURCE_SUFFIXES = {
    ".py",
    ".json",
    ".toml",
    ".md",
    ".yml",
    ".yaml",
}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "logs",
    "receipts",
    "dist",
    "build",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix in SOURCE_SUFFIXES:
            yield path


def write_manifest(root: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sha256", "path"])
        for path in iter_source_files(root):
            writer.writerow([sha256_file(path), path.relative_to(root).as_posix()])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Gate 1 execution receipt")
    parser.add_argument("--command", nargs="+", default=[sys.executable, "-m", "pytest", "-q"], help="Command to execute")
    parser.add_argument("--receipt", default="receipts/gate1/gate1_execution_receipt.json")
    parser.add_argument("--stdout", default="logs/gate1_stdout.log")
    parser.add_argument("--stderr", default="logs/gate1_stderr.log")
    parser.add_argument("--manifest", default="manifests/PRE_GATE_HASH_MANIFEST.csv")
    args = parser.parse_args()

    root = Path.cwd()
    receipt_path = root / args.receipt
    stdout_path = root / args.stdout
    stderr_path = root / args.stderr
    manifest_path = root / args.manifest

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    write_manifest(root, manifest_path)

    started = now_iso()
    completed_process = subprocess.run(
        args.command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    ended = now_iso()

    stdout_path.write_text(completed_process.stdout, encoding="utf-8")
    stderr_path.write_text(completed_process.stderr, encoding="utf-8")

    receipt = {
        "receipt_id": "gate1_execution_receipt",
        "receipt_type": "execution",
        "gate": "gate1",
        "command": " ".join(args.command),
        "status": "PASS" if completed_process.returncode == 0 else "FAIL",
        "exit_code": completed_process.returncode,
        "timestamp_start": started,
        "timestamp_end": ended,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "stdout_hash": sha256_file(stdout_path),
        "stderr_hash": sha256_file(stderr_path),
        "source_manifest": manifest_path.as_posix(),
        "source_manifest_hash": sha256_file(manifest_path),
        "output_manifest": None,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "cwd": str(root),
        },
        "authority_earned": False,
        "production_allowed": False,
        "clinical_allowed": False,
    }

    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return completed_process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
