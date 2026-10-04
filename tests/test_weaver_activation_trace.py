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
    assert [event["action"] for event in events] == [
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
    assert [event["action"] for event in recorder.events] == ["Reject"]
    assert recorder.events[0]["rejection_code"] == "MALFORMED_IDENTITY"
