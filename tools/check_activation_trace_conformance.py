"""Replay runtime-emitted activation traces through the WeaverActivation TLA+ model."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tools.run_activation_trace_corpus import run_corpus

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "audit-package" / "formal" / "tla+"
TRACE_SCHEMA = "weaver-activation-trace-1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_trace(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text().splitlines()):
        event = json.loads(line)
        if event.get("schema_version") != TRACE_SCHEMA:
            raise ValueError(f"{path.name}: unsupported trace schema")
        if event.get("seq") != index:
            raise ValueError(f"{path.name}: non-contiguous sequence at {index}")
        events.append(event)
    if not events:
        raise ValueError(f"{path.name}: empty trace")
    return events


def _record(fields: list[tuple[str, str]]) -> str:
    body = ", ".join(f'{key} |-> "{value}"' for key, value in fields)
    return f"[{body}]"


def _compile_trace(events: list[dict[str, Any]], trace_sha256: str) -> str:
    bound_backend: str | None = None
    bound_checkpoint: str | None = None
    bound_input: str | None = None
    rows: list[str] = []

    for event in events:
        action = str(event["action"])
        request = "R1"

        if action == "Authorize":
            row = _record(
                [
                    ("action", action),
                    ("request", request),
                    ("auth", "A1"),
                ]
            )
        elif action == "BindContract":
            bound_backend = str(event["backend_id"])
            bound_checkpoint = str(event["checkpoint_sha256"])
            bound_input = str(event["input_sha256"])
            row = _record(
                [
                    ("action", action),
                    ("request", request),
                    ("contract", "C1"),
                    ("backend", "B1"),
                    ("checkpoint", "CP1"),
                    ("input", "I1"),
                ]
            )
        elif action == "Execute":
            row = _record([("action", action), ("request", request)])
        elif action == "VerifyGood":
            if bound_backend is None or bound_checkpoint is None or bound_input is None:
                raise ValueError("VerifyGood appeared before BindContract")
            row = _record(
                [
                    ("action", action),
                    ("request", request),
                    (
                        "backend",
                        "B1" if str(event["backend_id"]) == bound_backend else "B2",
                    ),
                    (
                        "checkpoint",
                        "CP1"
                        if str(event["checkpoint_sha256"]) == bound_checkpoint
                        else "CP2",
                    ),
                    (
                        "input",
                        "I1" if str(event["input_sha256"]) == bound_input else "I2",
                    ),
                    ("output", "O1"),
                ]
            )
        elif action == "Reject":
            row = _record(
                [
                    ("action", action),
                    ("request", request),
                    ("code", str(event["rejection_code"])),
                ]
            )
        elif action == "RecordPass":
            row = _record([("action", action), ("request", request)])
        else:
            raise ValueError(f"unsupported activation trace action: {action}")
        rows.append(row)

    sequence = "<<\n    " + ",\n    ".join(rows) + "\n  >>"
    return (
        "---- MODULE GeneratedActivationTrace ----\n"
        f"\\* source_trace_sha256={trace_sha256}\n"
        f"RuntimeTrace == {sequence}\n"
        "====\n"
    )


def _run_tlc(jar: Path, generated: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="weaver-activation-trace-tlc-") as raw:
        directory = Path(raw)
        for name in (
            "WeaverActivation.tla",
            "WeaverActivationTrace.tla",
            "WeaverActivationTrace.cfg",
        ):
            shutil.copy2(FORMAL / name, directory / name)
        (directory / "GeneratedActivationTrace.tla").write_text(generated)
        return subprocess.run(
            [
                "java",
                "-cp",
                str(jar),
                "tlc2.TLC",
                "-deadlock",
                "-config",
                "WeaverActivationTrace.cfg",
                "WeaverActivationTrace.tla",
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=90,
        )


def _check_negative_controls(
    jar: Path,
    traces: dict[str, list[dict[str, Any]]],
    output: Path,
) -> list[dict[str, Any]]:
    mutations: list[tuple[str, list[dict[str, Any]]]] = []

    reordered = [dict(event) for event in traces["TRACE-001"]]
    reordered[1], reordered[2] = reordered[2], reordered[1]
    for index, event in enumerate(reordered):
        event["seq"] = index
    mutations.append(("execute-before-bind", reordered))

    wrong_phase = [dict(event) for event in traces["TRACE-006"]]
    wrong_phase[-1]["rejection_code"] = "AUTHORITY_INVALID"
    mutations.append(("post-execution-authority-reject", wrong_phase))

    results: list[dict[str, Any]] = []
    for name, events in mutations:
        generated = _compile_trace(events, "negative-control")
        generated_path = output / f"negative-{name}.tla"
        generated_path.write_text(generated)
        result = _run_tlc(jar, generated)
        log = (
            f"$ TLC negative control {name}\n"
            + result.stdout
            + "\n--- stderr ---\n"
            + result.stderr
        ).encode()
        log_path = output / f"negative-{name}-tlc.log"
        log_path.write_bytes(log)
        detected = result.returncode != 0
        results.append(
            {
                "mutation": name,
                "detected": detected,
                "returncode": result.returncode,
                "generated_tla": generated_path.name,
                "generated_tla_sha256": _sha256(generated.encode("utf-8")),
                "tlc_log": log_path.name,
                "tlc_log_sha256": _sha256(log),
            }
        )
    return results


def check_conformance(jar: Path, output: Path) -> dict[str, Any]:
    runtime_report = run_corpus(output)
    traces: dict[str, list[dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []

    for runtime_case in runtime_report["results"]:
        case_id = str(runtime_case["case_id"])
        trace_path = output / str(runtime_case["trace_file"])
        events = _load_trace(trace_path)
        traces[case_id] = events
        generated = _compile_trace(events, str(runtime_case["trace_sha256"]))
        generated_bytes = generated.encode("utf-8")
        generated_path = output / f"{case_id.lower()}-generated.tla"
        generated_path.write_bytes(generated_bytes)
        result = _run_tlc(jar, generated)
        log = (
            "$ TLC WeaverActivationTrace\n"
            + result.stdout
            + "\n--- stderr ---\n"
            + result.stderr
        ).encode()
        log_path = output / f"{case_id.lower()}-tlc.log"
        log_path.write_bytes(log)
        results.append(
            {
                "case_id": case_id,
                "status": "PASS" if result.returncode == 0 else "FAIL",
                "trace_sha256": runtime_case["trace_sha256"],
                "generated_tla": generated_path.name,
                "generated_tla_sha256": _sha256(generated_bytes),
                "tlc_log": log_path.name,
                "tlc_log_sha256": _sha256(log),
                "returncode": result.returncode,
            }
        )

    negative_controls = _check_negative_controls(jar, traces, output)
    report = {
        "schema": "weaver-activation-trace-conformance-1",
        "corpus_sha256": runtime_report["corpus_sha256"],
        "scope": runtime_report["scope"],
        "cases": results,
        "negative_controls": negative_controls,
    }
    report_path = output / "activation-trace-conformance-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if not all(item["status"] == "PASS" for item in results):
        raise SystemExit("activation trace TLC replay failed")
    if not all(item["detected"] for item in negative_controls):
        raise SystemExit("activation trace negative control survived")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jar", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check_conformance(args.jar.resolve(), args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
