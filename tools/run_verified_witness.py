"""Verify, extract, and execute one captured witness archive."""

import argparse
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from tools.verify_witness_archive import verify_archive_bytes


def run_verified_witness(archive: Path, expected_fingerprint: str) -> dict:
    raw = archive.read_bytes()
    digests = verify_archive_bytes(raw, expected_fingerprint)
    with tempfile.TemporaryDirectory(prefix="weaver-witness-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            # Names and file types were checked before any filesystem writes.
            for name in bundle.namelist():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(name))
        command = [sys.executable, "-E", "-s", "witness.py"]
        try:
            result = subprocess.run(
                command, cwd=root / "src", capture_output=True, text=True, timeout=30
            )
            execution = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            execution = {
                "returncode": None,
                "stdout": (exc.stdout or b"").decode("utf-8", errors="replace"),
                "stderr": (exc.stderr or b"").decode("utf-8", errors="replace"),
                "timed_out": True,
            }
    return {"schema": "weaver-bound-witness-run-1", **digests, **execution}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-key-sha256", required=True)
    args = parser.parse_args()
    receipt = run_verified_witness(args.archive, args.expected_key_sha256)
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if receipt["returncode"] == 0 and not receipt["timed_out"] else 1)


if __name__ == "__main__":
    main()
