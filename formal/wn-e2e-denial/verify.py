"""Recompile both files and retain genuine compiler results."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
for filename in ("Core.lean", "Denial.lean"):
    source = (root / filename).read_text()
    if re.search(r"\b(sorry|admit|axiom)\b", source):
        raise SystemExit(f"Forbidden placeholder/declaration in {filename}")
results = []
env = dict(os.environ)
for command in (
    ["lean", "--version"],
    ["lean", "--print-prefix"],
    ["lean", "-o", "Core.olean", "Core.lean"],
    ["lean", "Denial.lean"],
):
    try:
        p = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        result = {
            "command": command,
            "exit_code": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        result = {"command": command, "exit_code": None, "error": str(error)}
    results.append(result)
    if command == ["lean", "--print-prefix"] and result["exit_code"] == 0:
        env["LEAN_PATH"] = (
            str(root) + os.pathsep + str(Path(result["stdout"].strip()) / "lib/lean")
        )
    (root / "CHECK_RESULT.json").write_text(json.dumps(results, indent=2) + "\n")
    if result["exit_code"] != 0:
        print(json.dumps(result, indent=2))
        sys.exit(1)
print("PASS: both Lean files compiled; inspect CHECK_RESULT.json axiom output.")
