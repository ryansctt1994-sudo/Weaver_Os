"""Check that an evidence record still describes the code it sits next to.

    python -m tools.check_evidence_binding evidence/step6/WNS-S6-001-evidence.json

Passes only if every file whose SHA-256 the record holds is byte-identical in the working
tree. When git history is available, it also lists every file changed between the
record's commit and HEAD, so a reviewer can see that later commits only added evidence or
documentation. A mismatch means the record is stale: regenerate it, or mark it superseded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    record = json.loads(args.record.read_text(encoding="utf-8"))
    source = record["source"]
    mismatched = []
    for path, recorded in sorted(source["files_sha256"].items()):
        target = ROOT / path
        current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if current != recorded:
            mismatched.append(path)
        print(f"{'MATCH' if current == recorded else 'DIFF '}  {path}")
    commit = source["commit"]
    changed = subprocess.run(
        ["git", "diff", "--name-status", commit, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if changed.returncode == 0:
        lines = changed.stdout.strip().splitlines()
        print(f"files changed since the record's commit {commit[:12]}: {len(lines)}")
        for line in lines:
            print(f"  {line}")
    else:
        print(f"git history for {commit[:12]} not available; hash comparison only")
    if not source.get("tree_clean", False):
        print("FAIL: the record was generated from a dirty tree")
        return 1
    if mismatched:
        print(f"FAIL: {len(mismatched)} recorded file(s) differ; the record is stale")
        return 1
    print("OK: every recorded source file is identical to the working tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
