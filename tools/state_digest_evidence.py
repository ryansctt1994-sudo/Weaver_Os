"""Produce the WNS-S6-001 before/after evidence record.

    python -m tools.state_digest_evidence --out evidence/step6/WNS-S6-001-evidence.json

Run on a clean checkout. The record names the exact commit and refuses to claim more if
the tree is dirty. It keeps raw command output (stdout, stderr, exit codes) and negative
results alongside the positive ones.

This is origin-controlled evidence: same machine, same operator. It is R2[self], W0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from weaver_verifier.state import REDUCER_SOURCE_SHA256, state_report

from tools.state_controls import LEDGER_ID, build_demo_ledger, run_controls

ROOT = Path(__file__).resolve().parents[1]
BASE_BEFORE = "7b4c30a1dedd5b7a8f887e61ba0b998bae8f488c"  # main after PR #102, before Step 6
SOURCES = [
    "packages/verifier/weaver_verifier/state.py",
    "packages/verifier/weaver_verifier/ledger.py",
    "packages/contracts/weaver_contracts/canonical.py",
    "packages/contracts/weaver_contracts/ledger.py",
    "packages/contracts/weaver_contracts/receipt.py",
    "packages/runtime/weaver_runtime/ledger.py",
    "packages/runtime/weaver_runtime/gate.py",
    "tools/state_controls.py",
    "tools/export_ledger.py",
    "published_manifest.json",
    "kernel/reducer.py",
]
# Explicit import path for subprocesses, so they work whether or not the package is installed.
REPO_PYTHONPATH = os.pathsep.join(
    str(p) for p in [ROOT] + [ROOT / "packages" / d for d in ("contracts", "runtime", "verifier")]
)
STATE_MUTATIONS = {
    "state-chain-validation",
    "state-reconstruction",
    "state-source-binding",
    "state-digest-comparison",
    "state-duplicate-commit",
    "state-claim-comparison",
}


def run(cmd: list[str], *, cwd: Path = ROOT, env: dict | None = None, timeout: int = 600) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skip-mutations", action="store_true")
    args = parser.parse_args(argv)

    dirty = git("status", "--porcelain")
    record: dict = {
        "schema": "wns-s6-001-evidence-1",
        "milestone": "WNS-S6-001",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_level": "R2[self]",
        "witness": "W0",
        "authority": "NONE",
        "source": {
            "commit": git("rev-parse", "HEAD"),
            "tree_clean": dirty == "",
            "dirty_paths": dirty.splitlines(),
            "base_before_step6": BASE_BEFORE,
            "files_sha256": {
                path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCES
            },
            "reducer_source_sha256": REDUCER_SOURCE_SHA256,
        },
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "sqlite": sqlite3.sqlite_version,
        },
    }

    # --- before: what existed at the base commit ---------------------------------
    absent = run(["git", "show", f"{BASE_BEFORE}:packages/verifier/weaver_verifier/state.py"])
    kernel_symbol = run(
        [sys.executable, "-c", "import kernel.reducer as m; m.reduce"], env=dict(os.environ)
    )
    manifest = json.loads((ROOT / "published_manifest.json").read_text())
    record["before"] = {
        "in_tree_runtime_state_digest_at_base": (
            "ABSENT" if absent["exit_code"] != 0 else "PRESENT"
        ),
        "git_show_state_py_at_base": {k: absent[k] for k in ("exit_code", "stderr")},
        "manifest_state_digest": {
            key: manifest[key]
            for key in ("expected_state_digest", "state_digest_status", "state_digest_method")
        },
        "kernel_reducer_symbol_access": {k: kernel_symbol[k] for k in ("exit_code", "stderr")},
    }

    # --- after: computed digest, independent replay, E3.5 still held ------------
    with tempfile.TemporaryDirectory(prefix="wns-s6-") as directory:
        work = Path(directory)
        db = work / "demo.db"
        snapshot, anchor = build_demo_ledger(db)
        in_process = state_report(snapshot, anchor=anchor)
        export = run(
            [
                sys.executable, "-m", "tools.export_ledger", "--db", str(db),
                "--ledger-id", LEDGER_ID, "--snapshot-out", str(work / "s.json"),
                "--anchor-out", str(work / "a.json"),
            ],
            env={**os.environ, "PYTHONPATH": REPO_PYTHONPATH},
        )
        fresh_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join(
                [str(ROOT / "packages" / "contracts"), str(ROOT / "packages" / "verifier")]
            ),
        }
        fresh = [
            run(
                [sys.executable, "-S", "-m", "weaver_verifier.state",
                 "--snapshot", "s.json", "--anchor", "a.json"],
                cwd=work,
                env=fresh_env,
            )
            for _ in range(2)
        ]
        probe = run([sys.executable, "-S", "-c", "import weaver_runtime"], cwd=work, env=fresh_env)
        controls = run_controls(work / "controls")
    fresh_digests = sorted({json.loads(r["stdout"])["digest"] for r in fresh if r["stdout"]})
    record["after"] = {
        "in_process": {"status": in_process.status, "digest": in_process.digest},
        "export": {k: export[k] for k in ("exit_code", "stderr")},
        "fresh_process_runs": fresh,
        "fresh_process_digests": fresh_digests,
        "fresh_process_matches_in_process": fresh_digests == [in_process.digest],
        "fresh_process_cannot_import_runtime": probe["exit_code"] != 0,
        "e35": run([sys.executable, "verify_attestations.py", "--scope", "e35"]),
    }
    record["controls"] = [asdict(result) for result in controls]

    if not args.skip_mutations:
        mutations = run([sys.executable, "-m", "tools.check_verifier_mutations"], timeout=3600)
        try:
            results = json.loads(mutations["stdout"])["results"]
        except (ValueError, KeyError):
            results = []
        record["mutations"] = {
            "exit_code": mutations["exit_code"],
            "total": len(results),
            "detected": sum(bool(r["detected"]) for r in results),
            "state_mutations": [
                {k: r[k] for k in ("mutation", "detected", "returncode")}
                for r in results
                if r["mutation"] in STATE_MUTATIONS
            ],
        }

    record["status"] = {
        "E3.5": "HOLD" if record["after"]["e35"]["exit_code"] != 0 else "UNEXPECTED_PASS",
        "C-GATE-001": "OPEN",
        "C-CUSTODY-001": "OPEN",
        "all_controls_ok": all(result.ok for result in controls),
    }
    record["trust_boundaries"] = [
        "Origin-controlled run: same machine, same operator, same checkout. "
        "Not independent witnessing.",
        "A fresh process reproducing a digest shows determinism, not authenticity.",
        "Without an anchor held outside the operator's control, a complete self-consistent rewrite "
        "is indistinguishable from authentic history (control C4).",
        "An anchor or expected digest supplied by the same party proves nothing more (control C8); "
        "custody is never established by this check.",
        "The projection covers gate executions only; other Authority Root event types refuse.",
        "C-GATE-001 is untouched: a commit that slipped through the commit-boundary race is a "
        "valid ledger entry and is included in the state.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = (
        record["source"]["tree_clean"]
        and record["status"]["all_controls_ok"]
        and record["after"]["fresh_process_matches_in_process"]
        and record["status"]["E3.5"] == "HOLD"
        and (args.skip_mutations or record["mutations"]["exit_code"] == 0)
    )
    print(f"wrote {args.out}; ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
