"""Execute the frozen adversarial corpus and emit attributable structured evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "verification"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())

LEDGER_CASES = (
    ("ADV-001", "byte-tamper", "tampered.jsonl"),
    ("ADV-002", "ledger-truncation", "truncated.jsonl"),
    ("ADV-003", "key-substitution", "key-substitution.jsonl"),
    ("ADV-004", "empty-ledger", "empty.jsonl"),
    ("ADV-005", "duplicate-json-key", "duplicate-key.jsonl"),
)
MALFORMED_RECEIPT = ("ADV-006", "malformed-receipt", "malformed-receipt.json")


def _ledger_case(case_id: str, name: str, filename: str) -> dict:
    spec = next(case for case in MANIFEST["cases"] if case["file"] == filename)
    path = FIXTURES / filename
    raw = path.read_bytes()
    digest_ok = hashlib.sha256(raw).hexdigest() == spec["sha256"]
    command = [
        sys.executable,
        "-m",
        "tools.verify_triad_ledger",
        str(path),
        "--expected-head",
        spec.get("head", MANIFEST["head"]),
        "--trusted-key-sha256",
        MANIFEST["key_sha256"],
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    rejected = result.returncode != 0
    reason_ok = spec["error"] in result.stderr
    status = "PASS" if digest_ok and rejected and reason_ok else "FAIL"
    return {
        "case_id": case_id,
        "case_name": name,
        "expected_verdict": "REJECT",
        "observed_verdict": "REJECT" if rejected else "UNEXPECTED_PASS",
        "status": status,
        "failure_code": spec["error"] if rejected else "UNEXPECTED_ACCEPT",
        "fixture": filename,
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "exit_code": result.returncode,
    }


def _receipt_case() -> dict:
    case_id, name, filename = MALFORMED_RECEIPT
    spec = next(case for case in MANIFEST["receipt_cases"] if case["file"] == filename)
    path = FIXTURES / filename
    raw = path.read_bytes()
    digest_ok = hashlib.sha256(raw).hexdigest() == spec["sha256"]
    schema = json.loads((ROOT / "schemas" / "triad_receipt.schema.json").read_text())
    receipt = json.loads(raw)
    rejected = False
    message = ""
    try:
        Draft202012Validator(schema).validate(receipt)
    except ValidationError as exc:
        rejected = True
        message = exc.message

    reason_ok = spec["error"] in message
    status = "PASS" if digest_ok and rejected and reason_ok else "FAIL"
    return {
        "case_id": case_id,
        "case_name": name,
        "expected_verdict": "REJECT",
        "observed_verdict": "REJECT" if rejected else "UNEXPECTED_PASS",
        "status": status,
        "failure_code": message or "UNEXPECTED_ACCEPT",
        "fixture": filename,
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "exit_code": 1 if rejected else 0,
    }


def _baseline() -> dict:
    spec = next(case for case in MANIFEST["cases"] if case["file"] == "valid.jsonl")
    path = FIXTURES / "valid.jsonl"
    command = [
        sys.executable,
        "-m",
        "tools.verify_triad_ledger",
        str(path),
        "--expected-head",
        MANIFEST["head"],
        "--trusted-key-sha256",
        MANIFEST["key_sha256"],
        "--expected-file-sha256",
        spec["sha256"],
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    return {
        "name": "valid-ledger",
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    baseline = _baseline()
    results = [_ledger_case(*case) for case in LEDGER_CASES]
    results.append(_receipt_case())
    status = (
        "PASS"
        if baseline["status"] == "PASS" and all(item["status"] == "PASS" for item in results)
        else "FAIL"
    )
    document = {
        "schema": "weaver-adversarial-results-1",
        "baseline": baseline,
        "results": results,
        "status": status,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "cases": len(results), "output": str(args.output)}))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
