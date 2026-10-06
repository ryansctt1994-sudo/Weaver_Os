from dataclasses import replace

from triadic_controls.crypto.verifier import VerificationResult
from weaver_activation import (
    CONTRACT_VERSION,
    ActivationAction,
    ActivationIntent,
    ActivationRejectCode,
    ActivationStatus,
    BackendActivationResult,
    WeaverActivationAdapter,
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
        "backend_id": "weaver-native",
        "action": ActivationAction.INFER,
        "checkpoint_sha256": CP,
        "input_sha256": INP,
        "backend_sha256": None,
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
        backend_sha256=intent.backend_sha256,
        contract_version=intent.contract_version,
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


def test_exact_contract_passes_without_authority_gain():
    adapter = WeaverActivationAdapter(StubVerifier())
    evidence = execute(adapter)
    assert evidence.status is ActivationStatus.PASS
    assert evidence.contract_version == CONTRACT_VERSION
    assert evidence.contract_sha256 is not None
    assert len(evidence.contract_sha256) == 64
    assert evidence.authority_delta == 0


def test_invalid_authority_rejects_before_backend():
    adapter = WeaverActivationAdapter(StubVerifier(valid=False))
    hits = []

    def backend(intent):
        hits.append(intent)
        return backend_ok(intent)

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.AUTHORITY_INVALID.value
    assert not hits


def test_token_for_different_contract_is_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())
    intent = make_intent()
    other = make_intent(request_id="req-other")
    payload = build_activation_authority_payload(other, authority_level=3)
    evidence = execute(adapter, intent=intent, payload=payload)
    assert evidence.reject_code == ActivationRejectCode.AUTHORITY_BINDING_MISMATCH.value


def test_contract_hash_changes_when_backend_changes():
    first = make_intent(backend_sha256="d" * 64)
    second = make_intent(backend_sha256="e" * 64)
    assert first.contract_sha256() != second.contract_sha256()


def test_unsupported_contract_version_rejected_before_verifier():
    verifier = StubVerifier()
    adapter = WeaverActivationAdapter(verifier)
    intent = make_intent(contract_version="future-contract")
    evidence = execute(adapter, intent=intent)
    assert evidence.reject_code == ActivationRejectCode.CONTRACT_VERSION_MISMATCH.value
    assert verifier.calls == 0


def test_duplicate_request_never_executes_backend_twice():
    adapter = WeaverActivationAdapter(StubVerifier())
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
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), checkpoint_sha256="d" * 64)

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_backend_artifact_substitution_in_result_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())
    intent = make_intent(backend_sha256="d" * 64)

    def backend(intent):
        return replace(backend_ok(intent), backend_sha256="e" * 64)

    evidence = execute(adapter, intent=intent, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_result_contract_version_substitution_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), contract_version="old-contract")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_bad_output_digest_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), output_sha256="not-a-digest")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.RESULT_IDENTITY_MISMATCH.value


def test_malformed_backend_digest_rejected_before_verifier():
    verifier = StubVerifier()
    adapter = WeaverActivationAdapter(verifier)
    evidence = execute(adapter, intent=make_intent(backend_sha256="bad"))
    assert evidence.reject_code == ActivationRejectCode.MALFORMED_IDENTITY.value
    assert verifier.calls == 0


def test_invalid_retention_floor_rejected_before_verifier():
    verifier = StubVerifier()
    adapter = WeaverActivationAdapter(verifier)
    evidence = execute(adapter, intent=make_intent(retention_floor=1.1))
    assert evidence.reject_code == ActivationRejectCode.MALFORMED_IDENTITY.value
    assert verifier.calls == 0


def test_retention_floor_passes_at_threshold():
    adapter = WeaverActivationAdapter(StubVerifier())
    intent = make_intent(action=ActivationAction.TRAIN, retention_floor=0.999)
    evidence = execute(adapter, intent=intent)
    assert evidence.status is ActivationStatus.PASS


def test_retention_floor_fails_closed():
    adapter = WeaverActivationAdapter(StubVerifier())
    intent = make_intent(action=ActivationAction.TRAIN, retention_floor=1.0)
    evidence = execute(adapter, intent=intent)
    assert evidence.reject_code == ActivationRejectCode.RETENTION_GATE_FAILED.value


def test_invalid_retention_metric_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), retention_metric=1.5)

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.METRIC_INVALID.value


def test_nonfinite_primary_metric_rejected():
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(intent):
        return replace(backend_ok(intent), primary_metric=float("nan"))

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.METRIC_INVALID.value


def test_backend_exception_becomes_rejection_evidence():
    adapter = WeaverActivationAdapter(StubVerifier())

    def backend(_intent):
        raise RuntimeError("backend down")

    evidence = execute(adapter, backend=backend)
    assert evidence.reject_code == ActivationRejectCode.BACKEND_FAILED.value
    assert evidence.authority_delta == 0


def test_nonfinite_retention_floor_rejects_without_crashing_evidence() -> None:
    verifier = StubVerifier()
    adapter = WeaverActivationAdapter(verifier)
    intent = make_intent(retention_floor=float("nan"))
    evidence = adapter.execute(
        intent,
        authority_envelope={"fixture": True},
        authority_payload={"malformed": True},
        requested_level=3,
        backend=backend_ok,
    )
    assert evidence.status is ActivationStatus.REJECT
    assert evidence.reject_code == ActivationRejectCode.MALFORMED_IDENTITY.value
    assert evidence.contract_sha256 is None
    assert evidence.authority_delta == 0
    assert verifier.calls == 0


def test_every_rejection_has_code_and_zero_authority_delta() -> None:
    adapter = WeaverActivationAdapter(StubVerifier(valid=False))
    evidence = execute(adapter)
    assert evidence.status is ActivationStatus.REJECT
    assert evidence.reject_code
    assert evidence.authority_delta == 0
