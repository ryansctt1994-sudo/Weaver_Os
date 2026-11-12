"""Fail closed when the E3.5 check fails for reasons other than policy refusal.

A nonzero process exit alone is NOT evidence that the intended verifier ran.
This command checks both the successful local-spine positive control and
the E3.5-withheld negative control, retaining raw output for review.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LOCAL_REQUIRED = (
    "PASS authority_ledger_hash",
    "PASS manifest_hash",
    "PASS expected_head_hash",
    "PASS expected_state_digest",
    "PASS state_digest_method",
    "EVIDENCE_CEILING: LOCAL_DETERMINISTIC_CHECK",
    "AUTHORITY: O0",
    "RESULT: LOCAL_SPINE_VERIFIED",
)
E35_REQUIRED = (
    "FAIL release_commit: UNBOUND",
    "FAIL environment_status: DECLARED_NOT_REPLAYED",
    "FAIL state_digest_status: LOCAL_REDUCER_COMPUTED (runtime replay required)",
    "FAIL independent_reproduction: NOT_IMPLEMENTED_BY_LOCAL_VERIFIER",
    "RESULT: E3.5_WITHHELD",
)


def classify(
    local: subprocess.CompletedProcess[str], e35: subprocess.CompletedProcess[str]
) -> list[str]:
    """Require the exact bounded result, not merely a coincidental exit code."""
    errors: list[str] = []
    for name, completed, exit_code, required, result_line in (
        ("local-spine", local, 0, LOCAL_REQUIRED, "RESULT: LOCAL_SPINE_VERIFIED"),
        ("e35", e35, 1, E35_REQUIRED, "RESULT: E3.5_WITHHELD"),
    ):
        if completed.returncode != exit_code:
            errors.append(f"{name}:EXIT_CODE:{completed.returncode}:EXPECTED:{exit_code}")
        if completed.stderr.strip():
            errors.append(f"{name}:UNEXPECTED_STDERR")
        lines = completed.stdout.splitlines()
        for marker in required:
            if marker not in lines:
                errors.append(f"{name}:MISSING_MARKER:{marker}")
        if sum(line.startswith("RESULT: ") for line in lines) != 1:
            errors.append(f"{name}:AMBIGUOUS_RESULT_LINE")
        if lines.count(result_line) != 1:
            errors.append(f"{name}:WRONG_RESULT")
        if any("Traceback" in line or "ModuleNotFoundError" in line for line in lines):
            errors.append(f"{name}:EXCEPTION_OUTPUT")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("e35-output.txt"))
    args = parser.parse_args(argv)

    commands = {
        scope: [sys.executable, str(ROOT / "verify_attestations.py"), "--scope", scope]
        for scope in ("local-spine", "e35")
    }
    results: dict[str, subprocess.CompletedProcess[str]] = {}
    for scope, command in commands.items():
        try:
            results[scope] = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            # Record the execution failure, but never mistake it for a policy refusal.
            results[scope] = subprocess.CompletedProcess(command, 125, "", str(exc))

    errors = classify(results["local-spine"], results["e35"])
    record = {
        "schema": "weaver-e35-held-execution-check-v1",
        "source_head_claim": os.environ.get("WEAVER_SOURCE_HEAD_SHA"),
        "runner_git_sha_claim": os.environ.get("GITHUB_SHA"),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "status": "BOUNDED_E35_WITHHELD_CHECK" if not errors else "INVALID_HOLD_CHECK",
        "errors": errors,
        "commands": {
            scope: {
                "argv": commands[scope],
                "exit_code": results[scope].returncode,
                "stdout": results[scope].stdout,
                "stderr": results[scope].stderr,
            }
            for scope in ("local-spine", "e35")
        },
        "authority": "O0_WITHHELD",
        "witness": "W0",
        "independent_reproduction": "NOT_CLAIMED",
    }
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        print("REFUSED: invalid E3.5 hold check; " + "; ".join(errors), file=sys.stderr)
        return 1
    print("EXPECTED_E35_WITHHELD_VERIFIER_EXECUTED")
    print("LOCAL_SPINE_POSITIVE_CONTROL_PASS")
    print("EVIDENCE_CEILING: LOCAL_DETERMINISTIC_CHECK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
