from __future__ import annotations

import json

from triadic_controls.crypto.verifier import VerificationResult
from weaver_activation import (
    ActivationAction,
    ActivationIntent,
    BackendActivationResult,
    WeaverActivationAdapter,
    build_activation_authority_payload,
)
from weaver_activation.trace import TRACE_SCHEMA_VERSION, ActivationTraceRecorder

CP = "a" * 64
INP = "b" * 64
OUT = "c" * 64


class ValidVerifier:
    def verify_authority_token(self, envelope, requested_level, inner_payload=None):
        return VerificationResult(
            is_valid=True,
            ledger_event_type="TOKEN_SIGNATURE_VALIDATED",
            failure_codes=[],
            verified_issuers=["issuer"],
            verification_time="2026-10-04T00:00:00+00:00",
            effective_max_authority_level=requested_level,
        )


def _intent() -> ActivationIntent:
    return ActivationIntent(
        request_id="r1",
        model_id="model-1",
        backend_id="backend-1",
        action=ActivationAction.INFER,
        checkpoint_sha256=CP,
        input_sha256=INP,
    )


def _backend(intent: ActivationIntent) -> BackendActivationResult:
    return BackendActivationResult(
        request_id=intent.request_id,
        model_id=intent.model_id,
        backend_id=intent.backend_id,
        checkpoint_sha256=intent.checkpoint_sha256,
        output_sha256=OUT,
        retention_metric=1.0,
    )


def test_pass_trace_is_canonical_and_ordered():
    intent = _intent()
    recorder = ActivationTraceRecorder()
    adapter = WeaverActivationAdapter(ValidVerifier(), trace_recorder=recorder)
    adapter.execute(
        intent,
        authority_envelope={"fixture": True},
        authority_payload=build_activation_authority_payload(intent, authority_level=3),
        requested_level=3,
        backend=_backend,
    )

    events = recorder.events
    assert [event["seq"] for event in events] == list(range(len(events)))
    assert [
        event["action"]
        for event in events
        if event["action"] not in {"BeginAttempt", "TerminalReceipt"}
    ] == [
        "Authorize",
        "BindContract",
        "Execute",
        "VerifyGood",
        "RecordPass",
    ]
    assert all(event["schema_version"] == TRACE_SCHEMA_VERSION for event in events)

    lines = recorder.canonical_ndjson().decode().splitlines()
    decoded = [json.loads(line) for line in lines]
    assert decoded == list(events)
    assert len(recorder.sha256()) == 64


def test_pre_authority_rejection_has_no_authorize_event():
    intent = _intent()
    recorder = ActivationTraceRecorder()
    adapter = WeaverActivationAdapter(ValidVerifier(), trace_recorder=recorder)
    malformed = ActivationIntent(
        request_id=intent.request_id,
        model_id=intent.model_id,
        backend_id=intent.backend_id,
        action=intent.action,
        checkpoint_sha256="bad",
        input_sha256=intent.input_sha256,
    )
    adapter.execute(
        malformed,
        authority_envelope={"fixture": True},
        authority_payload={"malformed": True},
        requested_level=3,
        backend=_backend,
    )
    assert [
        event["action"]
        for event in recorder.events
        if event["action"] not in {"BeginAttempt", "TerminalReceipt"}
    ] == ["Reject"]
    assert recorder.events[1]["rejection_code"] == "MALFORMED_IDENTITY"


def test_duplicate_pre_state_is_prefix_bound(tmp_path):
    from tools.check_activation_trace_conformance import _compile_trace, _load_trace
    from tools.run_activation_trace_corpus import run_corpus

    run_corpus(tmp_path)
    events = _load_trace(tmp_path / "trace-010.ndjson")
    starts = [event for event in events if event["action"] == "BeginAttempt"]
    assert starts[1]["pre_state"]["consumed_request_ids"] == ["r1"]
    assert starts[1]["pre_state"]["execution_counts"] == {"r1": 1}
    assert starts[1]["pre_state"]["terminal_receipts"]["r1"]["state"] == "Recorded"
    generated = _compile_trace(events, "test")
    assert "RejectDuplicate" in generated
    assert sum(event["action"] == "Execute" for event in events) == 1


def test_altered_or_detached_continuation_fails(tmp_path):
    import copy

    import pytest

    from tools.check_activation_trace_conformance import _compile_trace, _load_trace
    from tools.run_activation_trace_corpus import run_corpus

    run_corpus(tmp_path)
    original = _load_trace(tmp_path / "trace-010.ndjson")
    start = next(
        i for i, event in enumerate(original) if event["action"] == "BeginAttempt" and i > 0
    )
    for key, value in [
        ("consumed_request_ids", []),
        ("execution_counts", {"r1": 0}),
        ("terminal_receipts", {}),
        ("prior_trace_sha256", "0" * 64),
    ]:
        mutated = copy.deepcopy(original)
        mutated[start]["pre_state"][key] = value
        with pytest.raises(ValueError, match="pre-state"):
            _compile_trace(mutated, "test")
    with pytest.raises(ValueError, match="pre-state"):
        _compile_trace(original[start:], "test")
    mutated = copy.deepcopy(original)
    mutated[5 + 1]["receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="receipt digest"):
        _compile_trace(mutated, "test")
