"""Execute the frozen Weaver activation transition corpus and emit NDJSON traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from triadic_controls.crypto.verifier import VerificationResult
from weaver_activation import (
    ActivationAction,
    ActivationIntent,
    BackendActivationResult,
    WeaverActivationAdapter,
    build_activation_authority_payload,
)
from weaver_activation.trace import ActivationTraceRecorder

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "activation_trace_corpus.json"

CP = "a" * 64
INP = "b" * 64
OUT = "c" * 64
BACKEND = "d" * 64


class CorpusVerifier:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid

    def verify_authority_token(
        self,
        envelope: dict[str, Any],
        requested_level: int,
        inner_payload: dict[str, Any] | None = None,
    ) -> VerificationResult:
        return VerificationResult(
            is_valid=self.valid,
            ledger_event_type=(
                "TOKEN_SIGNATURE_VALIDATED" if self.valid else "QUORUM_FAILED"
            ),
            failure_codes=[] if self.valid else ["INSUFFICIENT_QUORUM"],
            verified_issuers=["issuer"] if self.valid else [],
            verification_time="2026-10-04T00:00:00+00:00",
            effective_max_authority_level=requested_level if self.valid else None,
        )


def _base_intent() -> ActivationIntent:
    return ActivationIntent(
        request_id="r1",
        model_id="model-1",
        backend_id="backend-1",
        action=ActivationAction.INFER,
        checkpoint_sha256=CP,
        input_sha256=INP,
        backend_sha256=BACKEND,
    )


def _backend_ok(intent: ActivationIntent) -> BackendActivationResult:
    return BackendActivationResult(
        request_id=intent.request_id,
        model_id=intent.model_id,
        backend_id=intent.backend_id,
        checkpoint_sha256=intent.checkpoint_sha256,
        output_sha256=OUT,
        primary_metric=0.75,
        retention_metric=0.99,
        backend_sha256=intent.backend_sha256,
        contract_version=intent.contract_version,
    )


def _backend_fail(_intent: ActivationIntent) -> BackendActivationResult:
    raise RuntimeError("fixture backend failure")


def _backend_result_mismatch(intent: ActivationIntent) -> BackendActivationResult:
    return replace(_backend_ok(intent), checkpoint_sha256="e" * 64)


def _backend_metric_invalid(intent: ActivationIntent) -> BackendActivationResult:
    return replace(_backend_ok(intent), primary_metric=float("nan"))


def _backend_retention_failed(intent: ActivationIntent) -> BackendActivationResult:
    return replace(_backend_ok(intent), retention_metric=0.5)


def _run_case(case: dict[str, Any], trace: ActivationTraceRecorder):
    scenario = case["scenario"]
    intent = _base_intent()
    verifier = CorpusVerifier(valid=scenario != "authority_invalid")
    backend: Callable[[ActivationIntent], BackendActivationResult] = _backend_ok

    if scenario == "contract_version_mismatch":
        intent = replace(intent, contract_version="future-contract")
    elif scenario == "malformed_identity":
        intent = replace(intent, checkpoint_sha256="not-a-digest")
    elif scenario == "backend_failed":
        backend = _backend_fail
    elif scenario == "result_identity_mismatch":
        backend = _backend_result_mismatch
    elif scenario == "metric_invalid":
        backend = _backend_metric_invalid
    elif scenario == "retention_gate_failed":
        intent = replace(intent, retention_floor=1.0)
        backend = _backend_retention_failed

    payload = build_activation_authority_payload(intent, authority_level=3)
    if scenario == "authority_binding_mismatch":
        other = replace(intent, request_id="other-request")
        payload = build_activation_authority_payload(other, authority_level=3)

    adapter = WeaverActivationAdapter(verifier, trace_recorder=trace)
    return adapter.execute(
        intent,
        authority_envelope={"fixture": True},
        authority_payload=payload,
        requested_level=3,
        backend=backend,
    )


def run_corpus(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    corpus_bytes = CORPUS.read_bytes()
    corpus = json.loads(corpus_bytes)
    results: list[dict[str, Any]] = []

    for case in corpus["cases"]:
        recorder = ActivationTraceRecorder()
        evidence = _run_case(case, recorder)
        actions = [str(event["action"]) for event in recorder.events]
        expected_status = case["expected_status"]
        expected_code = case["expected_reject_code"]
        passed = (
            evidence.status.value == expected_status
            and evidence.reject_code == expected_code
            and actions == case["expected_actions"]
            and evidence.authority_delta == 0
        )

        trace_path = output / f"{case['case_id'].lower()}.ndjson"
        recorder.write(trace_path)
        results.append(
            {
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "status": "PASS" if passed else "FAIL",
                "runtime_status": evidence.status.value,
                "rejection_code": evidence.reject_code,
                "actions": actions,
                "trace_file": trace_path.name,
                "trace_sha256": recorder.sha256(),
            }
        )

    report = {
        "schema": "weaver-activation-trace-run-1",
        "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "scope": corpus["scope"],
        "results": results,
    }
    report_path = output / "activation-trace-runtime-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if not all(item["status"] == "PASS" for item in results):
        raise SystemExit("activation trace runtime corpus failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_corpus(args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
