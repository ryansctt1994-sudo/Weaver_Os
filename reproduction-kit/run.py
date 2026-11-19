"""Verify the handoff, then run frozen sources offline. Never promotes authority."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inside():
    out = Path("/results")
    with tarfile.open("/kit/sources.tar") as archive:
        archive.extractall("/work", filter="data")
    root = Path("/work/Weaver_Os")
    env = dict(os.environ)
    env["PYTHONPATH"] = ":".join(
        str(root / p)
        for p in [
            ".",
            "src",
            "packages/contracts",
            "packages/runtime",
            "packages/verifier",
            "packages/witness",
        ]
    )
    env["HYPOTHESIS_STORAGE_DIRECTORY"] = "/work/.hypothesis"
    commands = [
        ("environment", ["python", "-m", "pip", "freeze"], root),
        ("os-packages", ["dpkg-query", "-W"], root),
        ("weaver-collection", ["python", "-m", "pytest", "--collect-only", "-q"], root),
        ("weaver-tests", ["python", "-m", "pytest", "-q", "-ra"], root),
        ("cathedral-primitives", ["make", "test"], Path("/work/cathedral-verified")),
        (
            "cathedral-properties",
            ["python", "-m", "pytest", "-q", "test_concurrency.py"],
            Path("/work/cathedral-verified/chronicle"),
        ),
    ]
    results = []
    for name, command, cwd in commands:
        with (out / f"{name}.log").open("wb") as log:
            try:
                result = subprocess.run(
                    command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1200
                )
                code = result.returncode
            except subprocess.TimeoutExpired:
                log.write(b"\nBLOCKED: command exceeded 1200 seconds\n")
                code = 124
        results.append({"name": name, "command": command, "cwd": str(cwd), "exit_code": code})
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0 if all(r["exit_code"] == 0 for r in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-sha256", required=True, help="Obtain via a separately authenticated channel"
    )
    parser.add_argument("--output", type=Path, required=True, help="New directory, never reused")
    args = parser.parse_args()
    kit = Path(__file__).resolve().parent
    manifest = kit / "SHA256SUMS"
    if digest(manifest) != args.manifest_sha256:
        raise ValueError("manifest trust pin mismatch; refused before Docker load")
    entries = {}
    for line in manifest.read_text().splitlines():
        expected, name = line.split("  ", 1)
        if Path(name).name != name or name in entries:
            raise ValueError("invalid/duplicate manifest path")
        entries[name] = expected
        if digest(kit / name) != expected:
            raise ValueError(f"artifact digest mismatch: {name}")
    required = {"environment.tar", "sources.tar", "kit.json", "run.py"}
    if not required <= entries.keys():
        raise ValueError("incomplete handoff manifest")
    metadata = json.loads((kit / "kit.json").read_text())
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = {
        "manifest_sha256": args.manifest_sha256,
        "image_id": metadata["image_id"],
        "host_kernel": platform.platform(),
        "classification": "LOCAL_UNWITNESSED",
        "independent_receipt": None,
        "witness": "W0",
        "authority": "O0",
        "production": "PROHIBITED",
    }
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    with (out / "docker-load.log").open("wb") as log:
        subprocess.run(
            ["docker", "load", "-i", str(kit / "environment.tar")],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    command = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=256",
        "--tmpfs",
        "/tmp:rw,exec,size=1g",
        "--tmpfs",
        "/work:rw,exec,size=2g",
        "-v",
        f"{kit}:/kit:ro",
        "-v",
        f"{out}:/results:rw",
        "-e",
        "HOME=/tmp",
        metadata["image_id"],
        "python",
        "-c",
        "import sys; sys.path.insert(0, '/kit'); from run import inside; sys.exit(inside())",
    ]
    with (out / "container.log").open("wb") as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
    (out / "exit-code.txt").write_text(str(code) + "\n")
    (out / "SHA256SUMS").write_text(
        "".join(
            f"{digest(path)}  {path.name}\n" for path in sorted(out.iterdir()) if path.is_file()
        )
    )
    print(f"Exit {code}; logs: {out}; results manifest: {digest(out / 'SHA256SUMS')}")
    return code


if __name__ == "__main__":
    sys.exit(main())
