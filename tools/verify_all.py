"""Run the complete fail-closed verification gate and emit one evidence report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
KEY = "5ac8e9d25de8d37cd9165d4a7458c34634aeded53c1709573ddf4cc122bcefb9"
ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"
LOCKFILE = ROOT / "requirements-verification.lock"
FORMAL_DIR = ROOT / "audit-package" / "formal" / "tla+"
REQUIRED_VERIFIERS = (
    "unit_and_integration",
    "bound_witness",
    "mutation_suite",
    "adversarial_corpus",
    "installed_wheel",
    "formal_tlc",
    "static_analysis_strict",
)
IMPLEMENTATION_STATUS = {
    "chronicle": "DEFERRED_TO_BOUND_WITNESS",
    "kernel": "DEFERRED_TO_BOUND_WITNESS",
    "receipt": "DEFERRED_TO_BOUND_WITNESS",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str, default: str | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        if default is None:
            raise
        return default


def repository_name() -> str:
    configured = os.environ.get("GITHUB_REPOSITORY")
    if configured:
        return configured
    remote = git("config", "--get", "remote.origin.url", default="local/unknown")
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@github.com:"):
        return remote.split(":", 1)[1]
    marker = "github.com/"
    if marker in remote:
        return remote.split(marker, 1)[1]
    return remote


def _log_bytes(command: list[str], stdout: bytes, stderr: bytes) -> bytes:
    prefix = ("$ " + " ".join(command) + "\n").encode()
    return prefix + stdout + b"\n--- stderr ---\n" + stderr


def run_step(
    verifier: str,
    step: str,
    command: list[str],
    output: Path,
    *,
    cwd: Path = ROOT,
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute one required step; missing tools and timeouts are hard failures."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
        code = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        code = -1
        raw_stdout = getattr(exc, "stdout", None) or b""
        raw_stderr = getattr(exc, "stderr", None) or b""
        stdout = raw_stdout.encode() if isinstance(raw_stdout, str) else raw_stdout
        stderr = raw_stderr.encode() if isinstance(raw_stderr, str) else raw_stderr
        stderr += ("\n" + repr(exc)).encode()

    log = _log_bytes(command, stdout, stderr)
    filename = f"{verifier}--{step}.log"
    (output / filename).write_bytes(log)
    return {
        "step": step,
        "command": command,
        "exit_code": code,
        "status": "PASS" if code == 0 else "FAIL",
        "log": filename,
        "log_sha256": hashlib.sha256(log).hexdigest(),
    }


def verifier(name: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    status = "PASS" if steps and all(step["status"] == "PASS" for step in steps) else "FAIL"
    first_failure = next((step["exit_code"] for step in steps if step["status"] == "FAIL"), 0)
    return {"name": name, "status": status, "exit_code": first_failure, "steps": steps}


def run_simple_verifier(
    name: str, command: list[str], output: Path, *, timeout: int = 300
) -> dict[str, Any]:
    return verifier(name, [run_step(name, "run", command, output, timeout=timeout)])


def run_installed_wheel(output: Path) -> tuple[dict[str, Any], Path | None]:
    name = "installed_wheel"
    steps: list[dict[str, Any]] = []
    dist = ROOT / "dist"
    shutil.rmtree(dist, ignore_errors=True)

    steps.append(
        run_step(
            name,
            "build",
            [sys.executable, "-m", "build", "--no-isolation", "--wheel"],
            output,
            timeout=180,
        )
    )
    wheels = sorted(dist.glob("*.whl")) if dist.exists() else []
    if len(wheels) != 1:
        message = f"expected exactly one built wheel, found {len(wheels)}\n".encode()
        log = _log_bytes(["internal", "locate-wheel"], b"", message)
        filename = f"{name}--locate-wheel.log"
        (output / filename).write_bytes(log)
        steps.append(
            {
                "step": "locate-wheel",
                "command": ["internal", "locate-wheel"],
                "exit_code": -1,
                "status": "FAIL",
                "log": filename,
                "log_sha256": hashlib.sha256(log).hexdigest(),
            }
        )
        return verifier(name, steps), None

    wheel = wheels[0]
    with tempfile.TemporaryDirectory(prefix="weaver-wheel-") as directory:
        temp = Path(directory)
        env_dir = temp / "venv"
        env_python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        smoke = temp / "wheel_smoke.py"
        ledger = temp / "valid.jsonl"
        shutil.copy2(ROOT / "tests" / "integration" / "wheel_smoke.py", smoke)
        shutil.copy2(ROOT / "tests" / "fixtures" / "verification" / "valid.jsonl", ledger)

        steps.append(
            run_step(
                name,
                "create-venv",
                [sys.executable, "-m", "venv", str(env_dir)],
                output,
                timeout=120,
            )
        )
        steps.append(
            run_step(
                name,
                "install-locked-dependencies",
                [str(env_python), "-m", "pip", "install", "-r", str(LOCKFILE)],
                output,
                cwd=temp,
                timeout=300,
            )
        )
        steps.append(
            run_step(
                name,
                "install-wheel",
                [str(env_python), "-m", "pip", "install", "--no-deps", str(wheel)],
                output,
                cwd=temp,
                timeout=120,
            )
        )
        steps.append(
            run_step(
                name,
                "smoke",
                [str(env_python), "-I", str(smoke), str(ledger)],
                output,
                cwd=temp,
                timeout=60,
            )
        )

    return verifier(name, steps), wheel


def run_formal_tlc(output: Path) -> dict[str, Any]:
    name = "formal_tlc"
    steps: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="weaver-tlc-") as directory:
        jar = Path(directory) / "tla2tools.jar"
        steps.append(
            run_step(
                name,
                "acquire-pinned-tlc",
                [sys.executable, "-m", "tools.fetch_tlc", str(jar)],
                output,
                timeout=180,
            )
        )
        steps.append(
            run_step(
                name,
                "witness-boundary-invariants",
                [
                    "java",
                    "-cp",
                    str(jar),
                    "tlc2.TLC",
                    "-deadlock",
                    "-config",
                    "WitnessBoundary.cfg",
                    "WitnessBoundary.tla",
                ],
                output,
                cwd=FORMAL_DIR,
                timeout=180,
            )
        )
        steps.append(
            run_step(
                name,
                "activation-runtime-invariants",
                [
                    "java",
                    "-cp",
                    str(jar),
                    "tlc2.TLC",
                    "-deadlock",
                    "-config",
                    "WeaverActivation.cfg",
                    "WeaverActivation.tla",
                ],
                output,
                cwd=FORMAL_DIR,
                timeout=180,
            )
        )
        steps.append(
            run_step(
                name,
                "activation-runtime-mutation-probes",
                [
                    sys.executable,
                    "-m",
                    "tools.check_activation_tla_mutations",
                    str(jar),
                ],
                output,
                cwd=ROOT,
                timeout=180,
            )
        )
        steps.append(
            run_step(
                name,
                "activation-trace-conformance",
                [
                    sys.executable,
                    "-m",
                    "tools.check_activation_trace_conformance",
                    str(jar),
                    "--output",
                    str(output / "activation-trace"),
                ],
                output,
                cwd=ROOT,
                timeout=300,
            )
        )
    return verifier(name, steps)


def load_adversarial_results(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text())
        results = document["results"]
        return results if isinstance(results, list) else []
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return []


def flatten_commands(verifiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    commands = []
    for item in verifiers:
        for step in item["steps"]:
            commands.append(
                {
                    "verifier": item["name"],
                    "step": step["step"],
                    "command": step["command"],
                    "exit_code": step["exit_code"],
                    "status": step["status"],
                }
            )
    return commands


def build_evidence_manifest(output: Path, wheel: Path | None) -> tuple[dict[str, str], str]:
    candidates = [
        ROOT / "pyproject.toml",
        LOCKFILE,
        ROOT / ARCHIVE,
        ROOT / "schemas" / "verification_run.schema.json",
        ROOT / "schemas" / "triad_receipt.schema.json",
        ROOT / "schemas" / "activation_receipt.schema.json",
        FORMAL_DIR / "WeaverActivation.tla",
        FORMAL_DIR / "WeaverActivation.cfg",
        FORMAL_DIR / "WeaverActivationTrace.tla",
        FORMAL_DIR / "WeaverActivationTrace.cfg",
        ROOT / "tests" / "fixtures" / "activation_trace_corpus.json",
        ROOT / "weaver_activation" / "trace.py",
        ROOT / "tools" / "run_activation_trace_corpus.py",
        ROOT / "tools" / "check_activation_trace_conformance.py",
    ]
    candidates.extend(sorted((ROOT / "tests" / "fixtures" / "verification").glob("*")))
    candidates.extend(sorted(path for path in output.glob("*") if path.is_file()))
    if wheel is not None:
        candidates.append(wheel)

    hashes: dict[str, str] = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:
            label = path.name
        hashes[label] = sha256_file(path)

    manifest = {
        "schema": "weaver-evidence-manifest-1",
        "files": dict(sorted(hashes.items())),
    }
    manifest_path = output / "evidence-manifest.json"
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    manifest_path.write_bytes(manifest_bytes)
    return hashes, hashlib.sha256(manifest_bytes).hexdigest()


def is_valid_verdict(
    verifiers: list[dict[str, Any]],
    adversarial_results: list[dict[str, Any]],
    wheel_sha256: str | None,
    *,
    dirty: bool = False,
) -> bool:
    """PASS iff every required verifier/case passes for a clean, bound source tree."""
    if dirty:
        return False
    by_name = {item.get("name"): item for item in verifiers}
    if set(by_name) != set(REQUIRED_VERIFIERS):
        return False
    if any(by_name[name].get("status") != "PASS" for name in REQUIRED_VERIFIERS):
        return False
    case_ids = {item.get("case_id") for item in adversarial_results}
    if case_ids != {f"ADV-{index:03d}" for index in range(1, 7)}:
        return False
    if any(item.get("status") != "PASS" for item in adversarial_results):
        return False
    return (
        isinstance(wheel_sha256, str)
        and len(wheel_sha256) == 64
        and all(char in "0123456789abcdef" for char in wheel_sha256)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "verification-output")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    dirty_at_start = bool(git("status", "--porcelain", default=""))
    verified_commit = git("rev-parse", "HEAD")
    source_head = os.environ.get("WEAVER_SOURCE_HEAD_SHA") or verified_commit
    base_sha = os.environ.get("WEAVER_BASE_SHA") or git(
        "rev-parse", "HEAD^", default=verified_commit
    )

    verifiers = [
        run_simple_verifier(
            "unit_and_integration", [sys.executable, "-m", "pytest", "-q"], args.output
        ),
        run_simple_verifier(
            "bound_witness",
            [
                sys.executable,
                "-m",
                "tools.run_verified_witness",
                ARCHIVE,
                "--expected-key-sha256",
                KEY,
            ],
            args.output,
        ),
        run_simple_verifier(
            "mutation_suite",
            [sys.executable, "-m", "tools.check_verifier_mutations"],
            args.output,
        ),
    ]

    adversarial_path = args.output / "adversarial-results.json"
    verifiers.append(
        run_simple_verifier(
            "adversarial_corpus",
            [
                sys.executable,
                "-m",
                "tools.run_adversarial_corpus",
                "--output",
                str(adversarial_path),
            ],
            args.output,
        )
    )

    # Static analysis runs before wheel construction so generated build/lib
    # copies cannot masquerade as duplicate source modules.
    verifiers.append(
        verifier(
            "static_analysis_strict",
            [
                run_step(
                    "static_analysis_strict",
                    "ruff",
                    [sys.executable, "-m", "ruff", "check", "."],
                    args.output,
                    timeout=180,
                ),
                run_step(
                    "static_analysis_strict",
                    "mypy",
                    [sys.executable, "-m", "mypy", "."],
                    args.output,
                    timeout=300,
                ),
            ],
        )
    )
    wheel_verifier, wheel = run_installed_wheel(args.output)
    verifiers.append(wheel_verifier)
    verifiers.append(run_formal_tlc(args.output))

    adversarial_results = load_adversarial_results(adversarial_path)
    wheel_sha256 = sha256_file(wheel) if wheel is not None and wheel.is_file() else None
    artifact_hashes, manifest_sha256 = build_evidence_manifest(args.output, wheel)
    overall = (
        "PASS"
        if is_valid_verdict(
            verifiers, adversarial_results, wheel_sha256, dirty=dirty_at_start
        )
        else "FAIL"
    )

    report = {
        "schema_version": "1.0",
        "repository": repository_name(),
        "source_head_sha": source_head,
        "verified_commit_sha": os.environ.get("GITHUB_SHA") or verified_commit,
        "base_sha": base_sha,
        "dirty": dirty_at_start,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local-checks-not-independent-reproduction",
        "lockfile_sha256": sha256_file(LOCKFILE),
        "wheel_sha256": wheel_sha256,
        "environment": {
            "python_version": sys.version,
            "os": os.name,
            "platform": platform.platform(),
            "runner": os.environ.get("RUNNER_OS", "local"),
        },
        "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "commands": flatten_commands(verifiers),
        "verifiers": verifiers,
        "adversarial_results": adversarial_results,
        "artifact_hashes": artifact_hashes,
        "evidence_manifest_sha256": manifest_sha256,
        "implementation_status": IMPLEMENTATION_STATUS,
        "overall_verdict": overall,
    }

    canonical = args.output / "verification-report.json"
    compatibility = args.output / "report.json"
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    canonical.write_text(encoded)
    compatibility.write_text(encoded)

    schema = json.loads((ROOT / "schemas" / "verification_run.schema.json").read_text())
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
    except Exception as exc:
        print(f"verification report schema validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"status": overall, "report": str(canonical)}))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
