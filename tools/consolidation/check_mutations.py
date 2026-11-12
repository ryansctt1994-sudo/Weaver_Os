"""Independent control-removal checks for consolidated evidence tools."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROOF = "packages/verifier/weaver_verifier/public_log.py"
TEST = "tests/consolidation/test_public_log.py"
MUTANTS = [
    (
        "log-set-signature",
        PROOF,
        "    key.verify(\n"
        '        base64.b64decode(verification["signedEntryTimestamp"], validate=True),\n'
        "        canonical(signed),\n        ec.ECDSA(hashes.SHA256()),\n    )",
        "    pass",
        f"{TEST}::test_tampering_never_verifies[time]",
    ),
    (
        "log-checkpoint-signature",
        PROOF,
        "            key.verify(signature[4:], signed_checkpoint, ec.ECDSA(hashes.SHA256()))",
        "            pass",
        f"{TEST}::test_each_log_signature_is_checked[checkpoint]",
    ),
    (
        "finding-type-distinction",
        "tools/consolidation/findings.py",
        "_canonical_json(baseline_value) == _canonical_json(observed_value)",
        "baseline_value == observed_value",
        "tests/consolidation/test_findings.py::test_distinguishes_boolean_from_integer_measurement",
    ),
    (
        "asset-digest",
        "tools/consolidation/validate.py",
        'if hashlib.sha256(path.read_bytes()).hexdigest() != entry["target_sha256"]:',
        "if False:",
        "tests/consolidation/test_source_manifest.py::test_modified_asset_is_refused",
    ),
    (
        "advisory-runtime-separation",
        "tools/check_trust_domains.py",
        '"legacy", "evidence", "tools"',
        '"legacy", "evidence"',
        "tests/test_trust_domains.py::test_advisory_consolidation_tools_cannot_enter_the_runtime",
    ),
    (
        "claim-read-bound",
        "tools/claim_audit/claim_audit.py",
        "data = stream.read(MAX_BYTES + 1)",
        "data = stream.read()",
        "tests/consolidation/test_claim_audit.py::"
        "test_text_read_has_a_bound_before_allocating_the_contents",
    ),
    (
        "claim-root-path-screen",
        "tools/claim_audit/claim_audit.py",
        "if root is not None:",
        "if False:",
        "tests/consolidation/test_claim_audit.py::test_text_reader_refuses_a_symlinked_ancestor",
    ),
]


def run(root: Path, tests: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=90,
    )


def main() -> int:
    baseline = run(ROOT, ["tests/consolidation", "tests/test_trust_domains.py"])
    if baseline.returncode:
        print(baseline.stdout + baseline.stderr)
        raise SystemExit("consolidation mutation baseline failed")
    rows = []
    for name, filename, old, new, test in MUTANTS:
        with tempfile.TemporaryDirectory(prefix="weaver-consolidation-mutation-") as directory:
            target = Path(directory) / "repo"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    "build",
                    "dist",
                ),
            )
            path = target / filename
            source = path.read_text()
            if source.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {name}")
            path.write_text(source.replace(old, new, 1))
            result = run(target, [test])
            detected = result.returncode == 1 and "FAILED " in result.stdout
            detected = detected and "ERROR " not in result.stdout
            rows.append(
                {
                    "mutation": name,
                    "detected": detected,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
    print(json.dumps({"schema": "weaver-consolidation-mutations-1", "results": rows}, indent=2))
    return 0 if all(row["detected"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
