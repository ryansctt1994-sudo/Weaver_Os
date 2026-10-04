"""Compile the pinned Lean lattice library and audit every exported theorem."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "formal" / "lattice-core"
ALLOWED_AXIOMS = {"propext", "Quot.sound"}


def check(output: Path, lake: str = "lake", lean: str = "lean") -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (PROJECT / "lean-toolchain").read_text().strip() != "leanprover/lean4:v4.22.0":
        raise ValueError("Lean toolchain pin changed")
    commands = [
        ("version", [lean, "--version"]),
        ("clean", [lake, "clean"]),
        ("build", [lake, "build"]),
        ("axioms", [lake, "env", "lean", "-DwarningAsError=true", "Audit.lean"]),
    ]
    logs = {}
    for name, command in commands:
        run = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=180)
        log = run.stdout + run.stderr
        logs[name] = log
        (output / f"{name}.log").write_text(log)
        if run.returncode != 0 or re.search(r"\bwarning:", log, re.I):
            raise SystemExit(f"Lean {name} failed; see retained log")
        if name == "version" and "version 4.22.0," not in log:
            raise SystemExit("wrong Lean version")
    sources = sorted((PROJECT / "LatticeCore").glob("*.lean"))
    expected = set()
    for path in sources:
        source = path.read_text()
        if re.search(r"\b(sorry|admit|axiom)\b", source):
            raise SystemExit(f"untrusted proof declaration in {path.name}")
        expected.update(re.findall(r"^theorem (\w+)", source, re.M))
    matches = re.findall(
        r"'LatticeCore\.([^']+)' (?:depends on axioms: \[([^\]]*)\]"
        r"|does not depend on any axioms)",
        logs["axioms"],
    )
    audited = {
        name: sorted(a.strip() for a in axioms.split(",") if a.strip()) for name, axioms in matches
    }
    if not expected or set(audited) != expected or len(matches) != len(expected):
        raise SystemExit("theorem audit coverage mismatch")
    if any(set(axioms) - ALLOWED_AXIOMS for axioms in audited.values()):
        raise SystemExit("unapproved transitive axiom dependency")
    files = sources + [
        PROJECT / name
        for name in (
            "LatticeCore.lean",
            "Audit.lean",
            "lean-toolchain",
            "lakefile.toml",
            "lake-manifest.json",
        )
    ]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    if os.environ.get("CI") and dirty:
        raise SystemExit("CI verification requires a clean source tree")
    report = {
        "schema": "weaver-lattice-core-check-1",
        "status": "PASS",
        "source_head_sha": os.environ.get("WEAVER_SOURCE_HEAD_SHA", commit),
        "verified_commit_sha": commit,
        "dirty": dirty,
        "lean_version": logs["version"].strip(),
        "theorems": audited,
        "source_sha256": hashes,
        "logs_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in logs.items()},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lake", default="lake")
    parser.add_argument("--lean", default="lean")
    args = parser.parse_args()
    report = check(args.output, args.lake, args.lean)
    print(
        json.dumps(
            {
                "status": report["status"],
                "theorems": len(report["theorems"]),
                "source_head_sha": report["source_head_sha"],
                "dirty": report["dirty"],
            }
        )
    )


if __name__ == "__main__":
    main()
