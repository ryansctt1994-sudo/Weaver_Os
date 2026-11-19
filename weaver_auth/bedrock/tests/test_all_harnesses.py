"""
Weavers Covenant – Gate 1 Full Harness.

Runs admission/pathology controls plus positive and negative replay fixtures.
Optionally observes a local chronicle; absent input is NOT_ASSESSED.
Produces a test-only receipt without execution authority.
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


MAX_CHRONICLE_BYTES = 1_000_000


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _no_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def replay_verify(chronicle_path: Path) -> bool:
    """Check a nonempty local JSONL hash chain; this is not independent witnessing.

    A bare hash chain cannot detect a deleted *complete suffix* without a
    separately pinned terminal hash or manifest. Do not assert completeness.
    """
    try:
        raw = chronicle_path.read_bytes()
        if not raw or len(raw) > MAX_CHRONICLE_BYTES:
            return False
        lines = raw.decode("utf-8").splitlines()
        if not lines or any(not line.strip() for line in lines):
            return False
        prev_hash = "GENESIS"
        for line in lines:
            entry = json.loads(
                line, object_pairs_hook=_no_duplicate_keys,
                parse_constant=_no_json_constant,
            )
            if not isinstance(entry, dict):
                return False
            current_hash = entry.get("entry_hash")
            if (entry.get("prev_hash") != prev_hash
                    or not isinstance(current_hash, str)
                    or len(current_hash) != 64
                    or any(char not in "0123456789abcdef" for char in current_hash)):
                return False
            if current_hash != _hash_payload(prev_hash, entry):
                return False
            prev_hash = current_hash
        return True
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        return False


def replay_observation(chronicle_path: Path) -> tuple[str, bool, str | None]:
    """Distinguish absent operational input from failed local verification."""
    if not chronicle_path.exists():
        return "NOT_ASSESSED", False, None
    try:
        input_digest = hashlib.sha256(chronicle_path.read_bytes()).hexdigest()
    except OSError:
        return "FAILED", False, None
    verified = replay_verify(chronicle_path)
    return (
        "LOCAL_HASH_CHAIN_PASS" if verified else "FAILED",
        verified,
        input_digest,
    )


def checkout_commit() -> str:
    """Get the checked-out tree's commit, not an attacker-supplied CI label."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return "UNAVAILABLE"
    sha = result.stdout.strip()
    if (result.returncode or len(sha) != 40
            or any(char not in "0123456789abcdef" for char in sha)):
        return "UNAVAILABLE"
    return sha


def generate_receipt(
    tests_passed: bool, replay_status: str, replay_passed: bool,
    replay_input_sha256: str | None, source_commit: str,
) -> dict[str, Any]:
    # Never promote a green fixture/control harness to operational assurance.
    conformance_ok = (
        tests_passed and replay_status != "FAILED" and source_commit != "UNAVAILABLE"
    )
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gate": 1,
        "source_commit": source_commit,
        "replay_input_sha256": replay_input_sha256,
        "tests_passed": tests_passed,
        "replay_passed": replay_passed,
        "replay_status": replay_status,
        "scope": "LOCAL_CONFORMANCE_ONLY",
        "qualification": "NOT_ASSESSED",
        "authority": "NONE",
        "status": "TEST_ONLY_PASS" if conformance_ok else "FAILURE",
    }


def write_receipt(receipt: dict[str, Any]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    print("=== Running admission tests ===")
    admission_ok = run_pytest(TEST_DIR / "test_admission_kernel.py")

    print("=== Running pathology tests ===")
    pathology_ok = run_pytest(TEST_DIR / "test_pathology_scan.py")

    print("=== Running replay negative controls and valid fixture ===")
    controls_ok = run_pytest(TEST_DIR / "test_gate1_replay.py")

    print("=== Observing optional local chronicle (not independent evidence) ===")
    replay_status, replay_ok, input_digest = replay_observation(CHRONICLE_PATH)
    print(f"Operational replay: {replay_status}")

    tests_passed = admission_ok and pathology_ok and controls_ok
    receipt = generate_receipt(
        tests_passed, replay_status, replay_ok, input_digest, checkout_commit(),
    )
    write_receipt(receipt)

    print(f"\nReceipt written to {RECEIPT_PATH}")
    if receipt["status"] == "TEST_ONLY_PASS":
        print("GATE 1 TEST-ONLY CONFORMANCE PASSED; NO AUTHORITY GRANTED")
        sys.exit(0)

    print("GATE 1 FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
