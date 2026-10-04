"""Fixed adversarial corpus checked through the CLI in fresh processes."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/verification"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda c: c["file"])
def test_fixed_ledger_case(case):
    path = FIXTURES / case["file"]
    before = path.read_bytes()
    assert hashlib.sha256(before).hexdigest() == case["sha256"]
    command = [
        sys.executable,
        "-m",
        "tools.verify_triad_ledger",
        str(path),
        "--expected-head",
        case.get("head", MANIFEST["head"]),
        "--trusted-key-sha256",
        MANIFEST["key_sha256"],
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert path.read_bytes() == before
    if case["accept"]:
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["events"] == 3
        assert report["head"] == MANIFEST["head"]
        assert report["file_sha256"] == case["sha256"]
    else:
        assert result.returncode != 0
        assert case["error"] in result.stderr
