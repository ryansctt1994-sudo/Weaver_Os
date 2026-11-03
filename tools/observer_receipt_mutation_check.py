"""Reproduce the v0.3 observer strict-validation mutation check on an ephemeral checkout.

This tool temporarily substitutes the exact pre-hardening v0.3 adapter source,
runs the entire local test suite, verifies that named negative tests turn RED,
and restores the original source in a finally block. It does NOT create a
GitHub branch, execute protected effects, or certify an independent witness.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ADAPTER = Path("benchmarks/agent_reliability/live_adapter.py")
MUTANT_SOURCE_COMMIT = "8bdb74a7f325c1bc2c1e25ae8fd5c07137109233"
EXPECTED_RED = {
    "test_observer_requires_exact_classification_and_root_fields",
    "test_observer_rejects_malformed_records_without_exception",
    "test_malformed_input_decision_fails_closed_without_exception",
    "test_ambiguous_observer_json_is_unknown_not_a_valid_receipt[duplicate_head]",
    "test_ambiguous_observer_json_is_unknown_not_a_valid_receipt[float_zero]",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _run_tests(label: str, directory: Path) -> tuple[int, set[str], int]:
    xml_file = directory / f"{label}.xml"
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--junitxml", str(xml_file)],
        text=True, capture_output=True, check=False,
    )
    (directory / f"{label}.log").write_text(
        run.stdout + "\n--- STDERR ---\n" + run.stderr, encoding="utf-8"
    )
    root = ET.parse(xml_file).getroot() if xml_file.exists() else None
    failures: set[str] = set()
    count = 0
    if root is not None:
        for testcase in root.iter("testcase"):
            count += 1
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                failures.add(testcase.attrib.get("name", "<unnamed>"))
    return run.returncode, failures, count


def main() -> int:
    directory = Path("mutation-receipts")
    directory.mkdir(exist_ok=True)
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    expected_source = subprocess.check_output(
        ["git", "show", f"{MUTANT_SOURCE_COMMIT}:{ADAPTER}"]
    )
    original = ADAPTER.read_bytes()
    if original == expected_source:
        raise RuntimeError("control source equals test candidate: mutation not applied")
    if _git("status", "--porcelain", "--", str(ADAPTER)):
        raise RuntimeError("refuse mutation on a checkout with modified adapter source")

    baseline_rc, baseline_failures, baseline_count = _run_tests("baseline", directory)
    if baseline_rc != 0 or baseline_failures:
        raise RuntimeError("baseline is not green; see mutation-receipts/baseline.log")

    mutant_rc = -1
    mutant_failures: set[str] = set()
    mutant_count = 0
    try:
        ADAPTER.write_bytes(expected_source)
        mutant_rc, mutant_failures, mutant_count = _run_tests("mutant", directory)
    finally:
        ADAPTER.write_bytes(original)
        if ADAPTER.read_bytes() != original:
            raise RuntimeError("restoration failed")
        if _git("status", "--porcelain", "--", str(ADAPTER)):
            raise RuntimeError("restored adapter differs from pinned source")

    passed = mutant_rc == 1 and mutant_failures == EXPECTED_RED
    report = {
        "schema": "weaver-observer-mutation-control-v0.1",
        "baseline_commit": head,
        "baseline_tree": tree,
        "mutant_source_commit": MUTANT_SOURCE_COMMIT,
        "mutated_file": str(ADAPTER),
        "baseline_file_sha256": hashlib.sha256(original).hexdigest(),
        "mutant_file_sha256": hashlib.sha256(expected_source).hexdigest(),
        "baseline_exit": baseline_rc,
        "baseline_testcases": baseline_count,
        "mutant_exit": mutant_rc,
        "mutant_testcases": mutant_count,
        "expected_red": sorted(EXPECTED_RED),
        "actual_red": sorted(mutant_failures),
        "mutant_sensitivity_confirmed": passed,
        "scope": (
            "Local CI-runner source substitution; frozen v0.3 source; "
            "no protected effects; no independent witness or authority"
        ),
        "restored_original_bytes": True,
    }
    (directory / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
