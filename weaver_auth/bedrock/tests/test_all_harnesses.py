"""
Weavers Covenant – Gate 1 Full Harness
Runs admission kernel tests, pathology scan tests, and chronicle replay.
Produces execution_receipt.json on success.
"""
import sys
import subprocess
import json
import hashlib
import datetime
from pathlib import Path


def run_pytest(test_file: str) -> int:
    result = subprocess.run(
        ["pytest", "-q", test_file],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode


def replay_verify(chronicle_path: str) -> bool:
    """Minimal replay verification using chronicle hash chain."""
    with open(chronicle_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return True  # empty chronicle is trivially replayable for Gate 1 bootstrap

    prev_hash = None
    for line in lines:
        entry = json.loads(line)
        if prev_hash is None:
            prev_hash = entry.get("prev_hash", None)
        else:
            expected = hashlib.sha256(
                prev_hash.encode()
                + json.dumps(entry, sort_keys=True).encode()
            ).hexdigest()
            actual = entry.get("entry_hash", "")
            if actual != expected:
                return False
            prev_hash = actual
    return True


def generate_receipt(tests_passed: bool, replay_passed: bool) -> dict:
    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "gate": 1,
        "tests_passed": tests_passed,
        "replay_passed": replay_passed,
        "status": "SUCCESS" if (tests_passed and replay_passed) else "FAILURE",
    }


def main() -> None:
    print("=== Running admission tests ===")
    admission_ok = run_pytest("test_admission_kernel.py") == 0

    print("=== Running pathology tests ===")
    pathology_ok = run_pytest("test_pathology_scan.py") == 0

    chronicle_file = (
        Path(__file__).parent.parent
        / "chronicle"
        / "adjudication_chronicle.jsonl"
    )
    if not chronicle_file.exists():
        chronicle_file.parent.mkdir(parents=True, exist_ok=True)
        chronicle_file.touch()

    print("=== Running replay verification ===")
    replay_ok = replay_verify(str(chronicle_file))

    all_pass = admission_ok and pathology_ok and replay_ok
    receipt = generate_receipt(all_pass, replay_ok)
    receipt_path = Path(__file__).parent.parent.parent / "receipts" / "execution_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)

    print(f"\nReceipt written to {receipt_path}")
    if all_pass:
        print("GATE 1 PASSED")
        sys.exit(0)

    print("GATE 1 FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
