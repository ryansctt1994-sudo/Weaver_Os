from dataclasses import replace

from triadic_controls.crypto.verifier import VerificationResult
from weaver_void import (
    ActivationAction,
    ActivationIntent,
    ActivationRejectCode,
    ActivationStatus,
    BackendActivationResult,
    VoidActivationAdapter,
    build_activation_authority_payload,
)

CP = "a" * 64
INP = "b" * 64
OUT = "c" * 64


class StubVerifier:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid
        self.calls = 0

    def verify_authority_token(self, envelope, requested_level, inner_payload=None):
        self.calls += 1
        return VerificationResult(
            is_valid=self.valid,
            ledger_event_type="TOKEN_SIGNATURE_VALIDATED" if self.valid else "QUORUM_FAILED",
            failure_codes=[] if self.valid else ["INSUFFICIENT_QUORUM"],
            verified_issuers=["issuer"] if self.valid else [],
            verification_time="2026-10-04T00:00:00+00:00",
            effective_max_authority_level=requested_level if self.valid else None,
        )


def make_intent(**changes):
    values = {
        "request_id": "req-1",
        "model_id": "m1",
        "backend_id": "void-native",
        "action": ActivationAction.INFER,
        "checkpoint_sha256": CP,
        "input_sha256": INP,
        "retention_floor": None,
    }
    values.update(changes)
    return ActivationIntent(**values)


def backend_ok(intent):
    return BackendActivationResult(
        request_id=intent.request_id,
        model_id=intent.model_id,
        backend_id=intent.backend_id,
        checkpoint_sha256=intent.checkpoint_sha256,
        output_sha256=OUT,
        primary_metric=0.52,
        retention_metric=0.999,
    )


def execute(adapter, intent=None, payload=None, backend=backend_ok):
    intent = intent or make_intent()
    payload = payload or build_activation_authority_payload(intent, authority_level=3)
    return adapter.execute(
        intent,
        authority_envelope={"fixture": True},
        authority_payload=payload,
        requested_level=3,
        backend=backend,
    )


def test_verified_exact_binding_passes_without_authority_gain():
    adapter = VoidActivationAdapter(StubVerifier())
    evidence = execute(adapter)
    assert evidence.status is ActivationStatus.PASS
    assert evidence.authority_delta == 0
    assert evidence.reject_code is None


def test_invalid_authority_rejects_before_backend():
    verifier = StubVerifier(valid=False)
    adapter = VoidActivationAdapter(verifier)
    hits = []

    def backend(intent):
        hits.append(intent)
        return backend_ok(intent)

    evidence = execute(adapter, backend=backend)
    assert evidence.status is ActivationStatus.REJECT
    assert evidence.reject_code == ActivationRejectCode.AUTHORITY_INVALID.value
    assert not hits


def test_valid_token_for_different_activation_is_rejected():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent()
    different = make_intent(request_id="req-other")
    payload = build_activation_authority_payload(different, authority_level=3)
    evidence = execute(adapter, intent=intent, payload=payload)
    assert evidence.reject_code == ActivationRejectCode.AUTHORITY_BINDING_MISMATCH.value


def test_duplicate_request_never_executes_backend_twice():
    adapter = VoidActivationAdapter(StubVerifier())
    hits = []

    def backend(intent):
        hits.append(intent.request_id)
        return backend_ok(intent)

    first = execute(adapter, backend=backend)
    second = execute(adapter, backend=backend)
    assert first.status is ActivationStatus.PASS
    assert second.reject_code == ActivationRejectCode.DUPLICATE_REQUEST.value
    assert hits == ["req-1"]


def test_checkpoint_substitution_in_result_rejected():
    adapter = VoidActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), checkpoint_sha256="d" * 64)

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_request_substitution_in_result_rejected():
    adapter = VoidActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), request_id="evil")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_bad_output_digest_rejected():
    adapter = VoidActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), output_sha256="not-a-digest")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_retention_floor_passes_at_threshold():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent(action=ActivationAction.TRAIN, retention_floor=0.999)
    evidence = execute(adapter, intent=intent)
    assert evidence.status is ActivationStatus.PASS


def test_retention_floor_fails_closed():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent(action=ActivationAction.TRAIN, retention_floor=1.0)
    evidence = execute(adapter, intent=intent)
    assert evidence.reject_code == ActivationRejectCode.RETENTION_GATE_FAILED.value


def test_missing_retention_metric_fails_closed():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent(action=ActivationAction.TRAIN, retention_floor=0.5)

    def backend(intent):
        return replace(backend_ok(intent), retention_metric=None)

    evidence = execute(adapter, intent=intent, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RETENTION_GATE_FAILED.value


def test_backend_exception_becomes_rejection_evidence():
    adapter = VoidActivationAdapter(StubVerifier())

    def backend(_intent):
        raise RuntimeError("backend down")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.BACKEND_FAILED.value
    assert evidence.authority_delta == 0


def test_malformed_checkpoint_rejected_before_authority_verifier():
    verifier = StubVerifier()
    adapter = VoidActivationAdapter(verifier)
    evidence = execute(adapter, intent=make_intent(checkpoint_sha256="bad"))
    assert evidence.reject_code == ActivationRejectCode.MALFORMED_IDENTITY.value
    assert verifier.calls == 0


def test_payload_builder_binds_exact_activation_tuple():
    intent = make_intent(action=ActivationAction.TRAIN)
    payload = build_activation_authority_payload(intent, authority_level=3)
    assert payload["scope"]["activation"] == intent.authority_binding()
    assert payload["scope"]["task"] == "neural_activation"
    assert payload["scope"]["region"] == "m1"


def test_backend_digest_is_bound_end_to_end():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent(backend_sha256="d" * 64)

    def backend(intent):
        return replace(backend_ok(intent), backend_sha256=intent.backend_sha256)

    evidence = execute(adapter, intent=intent, backend=backend)
    assert evidence.status is ActivationStatus.PASS
    assert evidence.backend_sha256 == "d" * 64


def test_backend_binary_substitution_in_result_rejected():
    adapter = VoidActivationAdapter(StubVerifier())
    intent = make_intent(backend_sha256="d" * 64)

    def backend(intent):
        return replace(backend_ok(intent), backend_sha256="e" * 64)

    evidence = execute(adapter, intent=intent, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_malformed_backend_digest_rejected_before_authority_verifier():
    verifier = StubVerifier()
    adapter = VoidActivationAdapter(verifier)
    evidence = execute(adapter, intent=make_intent(backend_sha256="not-a-digest"))
    assert evidence.reject_code == ActivationRejectCode.MALFORMED_IDENTITY.value
    assert verifier.calls == 0
