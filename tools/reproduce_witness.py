"""Run the sealed RC1 demonstration and preserve an unsigned operator evidence bundle."""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"
KEY = "5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9"
CHECKS = (
    "AUTHORIZED", "UNAUTHORIZED", "STATE PRESERVED", "REPLAY REJECTED", "FRESH REPLAY",
    "RECEIPT BASELINE", "RECEIPT TAMPER", "CHRONICLE TAMPER", "IDENTITY SWAP",
)


def assess(result: dict, expected_archive: str) -> dict[str, bool]:
    """Require every named check and successful execution on the sealed archive."""
    output = result.get("stdout", "")
    checks = {
        name: len(re.findall(rf"^{re.escape(name)}\.+PASS$", output, re.MULTILINE)) == 1
        for name in CHECKS
    }
    checks["EXECUTION"] = result.get("returncode") == 0 and result.get("timed_out") is False
    checks["SEALED ARCHIVE"] = result.get("archive_sha256") == expected_archive
    checks["WITNESS SUMMARY"] = len(re.findall(r"^WITNESS: PASS$", output, re.MULTILINE)) == 1
    checks["NO FAILED CHECK"] = not re.search(r"\bFAIL\b", output)
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--operator", required=True, help="Operator's declared identity")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    receipt = {
        "schema": "weaver-reproduction-outcome-1", "operator_declared": args.operator,
        "independence": "NOT_ADJUDICATED", "signature": "NOT_YET_SIGNED",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(), "status": "ERROR",
        "scope": "RC1 constructed commands; no production or Academy behavioral claim",
    }
    command = [sys.executable, "-E", "-s", "-m", "tools.run_verified_witness", ARCHIVE,
               "--expected-key-sha256", KEY]
    receipt["command"] = command
    receipt["cwd"] = str(ROOT)
    stdout, stderr = "", ""
    try:
        seal_bytes = (ROOT / "docs/releases/reproduction-seal.json").read_bytes()
        (args.output / "reproduction-seal.json").write_bytes(seal_bytes)
        seal = json.loads(seal_bytes)
        for name, digest in seal["files"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"sealed file mismatch: {name}")
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        stdout, stderr = run.stdout, run.stderr
        receipt["runner_exit_code"] = run.returncode
        result = json.loads(stdout)
        receipt["checks"] = assess(result, seal["files"][ARCHIVE])
        receipt["status"] = (
            "PASS" if run.returncode == 0 and all(receipt["checks"].values()) else "FAIL"
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
        receipt["error"] = "runner exceeded 60-second limit"
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (args.output / "runner.stdout.txt").write_text(stdout, encoding="utf-8")
    (args.output / "runner.stderr.txt").write_text(stderr, encoding="utf-8")
    (args.output / "outcome.json").write_text(json.dumps(receipt, indent=2) + "\n")
    files = sorted(args.output.iterdir())
    (args.output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files
    ))
    for name, passed in receipt.get("checks", {}).items():
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"{receipt['status']} in {receipt['elapsed_seconds']} seconds; evidence: {args.output}")
    print("Unsigned operator result; independent review and signature still required.")
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
