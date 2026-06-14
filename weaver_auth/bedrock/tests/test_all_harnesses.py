"""
Weavers Covenant – Gate 1 Full Harness.

Runs admission kernel tests, pathology scan tests, and chronicle replay.
Produces execution_receipt.json on success.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_DIR = Path(__file__).resolve().parent
BEDROCK_DIR = TEST_DIR.parent
RECEIPT_PATH = REPO_ROOT / "weaver_auth" / "receipts" / "execution_receipt.json"
CHRONICLE_PATH = BEDROCK_DIR / "chronicle" / "adjudication_chronicle.jsonl"


def run_pytest(test_file: Path) -> bool:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(test_file)],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode == 0


def _hash_payload(prev_hash: str, entry: dict[str, Any]) -> str:
    payload = {key: value for key, value in entry.items() if key != "entry_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(prev_hash.encode() + canonical).hexdigest()


def replay_verify(chronicle_path: Path) -> bool:
    """Verify a minimal chronicle hash chain."""
    if not chronicle_path.exists():
        return True

    lines = [line.strip() for line in chronicle_path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return True

    prev_hash = "GENESIS"
    for line in lines:
        entry = json.loads(line)
        if entry.get("prev_hash") != prev_hash:
            return False
        if entry.get("entry_hash") != _hash_payload(prev_hash, entry):
            return False
        prev_hash = entry["entry_hash"]
    return True


def generate_receipt(tests_passed: bool, replay_passed: bool) -> dict[str, Any]:
    return {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "gate": 1,
        "tests_passed": tests_passed,
        "replay_passed": replay_passed,
        "status": "SUCCESS" if tests_passed and replay_passed else "FAILURE",
    }


def write_receipt(receipt: dict[str, Any]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    print("=== Running admission tests ===")
    admission_ok = run_pytest(TEST_DIR / "test_admission_kernel.py")

    print("=== Running pathology tests ===")
    pathology_ok = run_pytest(TEST_DIR / "test_pathology_scan.py")

    print("=== Running replay verification ===")
    replay_ok = replay_verify(CHRONICLE_PATH)

    tests_passed = admission_ok and pathology_ok
    receipt = generate_receipt(tests_passed, replay_ok)
    write_receipt(receipt)

    print(f"\nReceipt written to {RECEIPT_PATH}")
    if tests_passed and replay_ok:
        print("GATE 1 PASSED")
        sys.exit(0)

    print("GATE 1 FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
