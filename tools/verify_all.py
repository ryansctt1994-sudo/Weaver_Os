"""Run the required local checks and retain a schema-validated evidence report."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
KEY = "5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9"
ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"


def run_check(name, command, output, timeout=300):
    """Missing programs and timeouts are failures, with logs retained."""
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        code = -1
        stdout = getattr(exc, "stdout", None) or b""
        stderr = (getattr(exc, "stderr", None) or b"") + str(exc).encode()
    log = stdout + b"\n--- stderr ---\n" + stderr
    (output / f"{name}.log").write_bytes(log)
    return {
        "name": name,
        "command": command,
        "returncode": code,
        "status": "PASS" if code == 0 else "FAIL",
        "log": f"{name}.log",
        "log_sha256": hashlib.sha256(log).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "verification-output")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    commands = [
        ("tests", [sys.executable, "-m", "pytest", "-q"]),
        (
            "witness",
            [
                sys.executable,
                "-m",
                "tools.run_verified_witness",
                ARCHIVE,
                "--expected-key-sha256",
                KEY,
            ],
        ),
        ("mutations", [sys.executable, "-m", "tools.check_verifier_mutations"]),
    ]
    checks = [run_check(name, cmd, args.output) for name, cmd in commands]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    paths = ["pyproject.toml", ARCHIVE, "requirements-verification.lock"]
    paths += [
        str(p.relative_to(ROOT))
        for p in sorted((ROOT / "tests/fixtures/verification").glob("*"))
        if p.is_file()
    ]
    paths += subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    paths = sorted({p for p in paths if (ROOT / p).is_file()})
    artifacts = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    report = {
        "schema": "weaver-verification-run-1",
        "commit": commit,
        "dirty": dirty,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": sys.version, "platform": platform.platform()},
        "scope": "local-checks-not-independent-reproduction",
        "artifacts": artifacts,
        "checks": checks,
        "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
    }
    schema = json.loads((ROOT / "schemas/verification_run.schema.json").read_text())
    Draft202012Validator(schema).validate(report)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(args.output / "report.json")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
