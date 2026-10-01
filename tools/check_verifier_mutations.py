"""Require targeted verifier gate removals to be detected by adversarial tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MUTATIONS = [
    (
        "archive-key-pin",
        "tools/verify_witness_archive.py",
        "if fingerprint != expected_fingerprint:",
        "if False:",
        "tests/test_witness_archive.py::test_whole_signature_substitution_is_rejected",
    ),
    (
        "archive-signature",
        "tools/verify_witness_archive.py",
        "Ed25519PublicKey.from_public_bytes(public).verify(signature, manifest_bytes)",
        "pass  # intentionally disabled by mutation probe",
        "tests/test_witness_archive.py::test_invalid_signature_is_rejected",
    ),
    (
        "archive-payload-hash",
        "tools/verify_witness_archive.py",
        "if hashlib.sha256(bundle.read(name)).hexdigest() != digest:",
        "if False:",
        "tests/test_witness_archive.py::test_payload_mutation_is_rejected",
    ),
    (
        "ledger-key-pin",
        "tools/verify_triad_ledger.py",
        "if hashlib.sha256(key).hexdigest() != trusted_key_sha256:",
        "if False:",
        "tests/test_triad_multiblock.py::test_truncation_and_fully_resigned_rewrite_fail",
    ),
    (
        "ledger-head-pin",
        "tools/verify_triad_ledger.py",
        'if events[-1]["event_hash"] != expected_head:',
        "if False:",
        "tests/test_triad_multiblock.py::test_truncation_and_fully_resigned_rewrite_fail",
    ),
    (
        "ledger-chain-integrity",
        "tools/verify_triad_ledger.py",
        "events = verify_chain(events)",
        "events = events",
        "tests/test_triad_multiblock.py::test_three_events_and_middle_byte_tamper",
    ),
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_witness_archive.py",
            "tests/test_triad_multiblock.py",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if baseline.returncode:
        print(baseline.stdout + baseline.stderr)
        raise SystemExit("mutation baseline failed")

    results = []
    for name, filename, old, new, test in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="weaver-mutation-") as directory:
            checkout = Path(directory) / "repo"
            shutil.copytree(
                root,
                checkout,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                    ".mypy_cache",
                    "build",
                    "dist",
                ),
            )
            target = checkout / filename
            source = target.read_text()
            if source.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {name}")
            target.write_text(source.replace(old, new, 1))
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", test],
                cwd=checkout,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Collection failures and crashes do not count as detected mutations.
            killed = result.returncode == 1 and "FAILED " in result.stdout
            killed = killed and "ERROR " not in result.stdout
            results.append(
                {
                    "mutation": name,
                    "detected": killed,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
    print(json.dumps({"schema": "weaver-verifier-mutations-1", "results": results}, indent=2))
    raise SystemExit(0 if all(result["detected"] for result in results) else 1)


if __name__ == "__main__":
    main()
