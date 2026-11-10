"""Verify that local evidence records still describe in-checkout source bytes.

This is source/hash consistency, NOT signature verification, witness custody or
authority. In particular, a self-updated record and self-updated source can
still agree while both are untrusted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate evidence JSON key: {key}")
        obj[key] = value
    return obj


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"nonfinite evidence JSON: {token}")


def _source_file(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("source path is not a safe repository-relative POSIX path")
    rel = PurePosixPath(value)
    if (
        rel.is_absolute() or ".." in rel.parts
        or str(rel) != value or not rel.parts
    ):
        raise ValueError(f"noncanonical or escaping source path: {value!r}")
    target = root
    # Check every segment, not only the final file: an in-checkout directory
    # symlink can otherwise alias a different source path while hashes match.
    for component in rel.parts:
        target = target / component
        if target.is_symlink():
            raise ValueError(f"symlinked source path component: {value!r}")
    if not target.resolve(strict=False).is_relative_to(root.resolve()):
        raise ValueError(f"escaping source path: {value!r}")
    return target


def _record_source(path: Path) -> tuple[str, bool, dict[str, str]]:
    document = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys, parse_constant=_reject_nonfinite,
    )
    if not isinstance(document, dict) or not isinstance(document.get("source"), dict):
        raise ValueError("missing evidence source object")
    source = document["source"]
    commit = source.get("commit")
    clean = source.get("tree_clean")
    files = source.get("files_sha256")
    if not isinstance(commit, str) or _COMMIT.fullmatch(commit) is None:
        raise ValueError("invalid source commit identity")
    if type(clean) is not bool:
        raise ValueError("tree_clean must be a literal JSON boolean")
    if not isinstance(files, dict) or not files:
        raise ValueError("missing recorded source digests")
    for value in files.values():
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError("invalid recorded SHA-256 digest")
    return commit, clean, files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    try:
        commit, clean, source_hashes = _record_source(args.record)
        # Reject the complete request before reading any source file or
        # printing a misleading per-file MATCH result.
        paths = {
            relative: _source_file(ROOT, relative)
            for relative in sorted(source_hashes)
        }
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"FAIL: evidence record input refused: {type(exc).__name__}: {exc}")
        return 1

    mismatched = []
    for relative, recorded in sorted(source_hashes.items()):
        target = paths[relative]
        try:
            current = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            current = None
        if current != recorded:
            mismatched.append(relative)
        print(f"{'MATCH' if current == recorded else 'DIFF '}  {relative}")
    changed = subprocess.run(
        ["git", "diff", "--name-status", commit, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if changed.returncode == 0:
        lines = changed.stdout.strip().splitlines()
        print(f"files changed since the record's commit {commit[:12]}: {len(lines)}")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"git history for {commit[:12]} not available; hash comparison only")
    if clean is not True:
        print("FAIL: the record was generated from a dirty tree")
        return 1
    if mismatched:
        print(f"FAIL: {len(mismatched)} recorded file(s) differ; the record is stale")
        return 1
    print("OK: every recorded source file matches the local record")
    print("NOTE: self-reported hashes do not prove provenance or external witness custody")
    return 0


if __name__ == "__main__":
    sys.exit(main())
