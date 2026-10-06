from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from weaver_activation import (
    RECEIPT_SCHEMA_VERSION,
    ActivationEvidence,
    ActivationReceipt,
    ActivationStatus,
)

D = "d" * 64
E = "e" * 64
F = "f" * 64
A = "a" * 64
B = "b" * 64
C = "c" * 64


def pass_evidence() -> ActivationEvidence:
    return ActivationEvidence(
        status=ActivationStatus.PASS,
        request_id="req-1",
        model_id="m1",
        backend_id="weaver-native",
        contract_version="weaver-activation-contract-1",
        contract_sha256=D,
        authority_event_type="TOKEN_SIGNATURE_VALIDATED",
        authority_payload_sha256=E,
        intent_sha256=F,
        result_sha256=A,
        checkpoint_sha256=B,
        input_sha256=C,
        output_sha256=D,
        primary_metric=0.75,
        retention_metric=0.999,
        reject_code=None,
        backend_sha256=E,
        authority_delta=0,
    )


def test_pass_receipt_is_canonical_and_schema_valid() -> None:
    receipt = ActivationReceipt.from_evidence(pass_evidence(), authority_event_id="auth-1")
    assert receipt.schema_version == RECEIPT_SCHEMA_VERSION
    assert receipt.verdict == "PASS"
    assert receipt.rejection_code is None
    assert receipt.authority_delta == 0
    assert len(receipt.sha256()) == 64

    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "activation_receipt.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(receipt.canonical_dict())


def test_reject_receipt_omits_nonfinite_metric_but_binds_result_hash() -> None:
    evidence = replace(
        pass_evidence(),
        status=ActivationStatus.REJECT,
        primary_metric=float("nan"),
        output_sha256=None,
        reject_code="METRIC_INVALID",
    )
    receipt = ActivationReceipt.from_evidence(evidence)
    assert receipt.verdict == "REJECT"
    assert receipt.rejection_code == "METRIC_INVALID"
    assert receipt.result_sha256 == A
    assert dict(receipt.normalized_metrics) == {"retention": 0.999}


def test_pass_receipt_refuses_missing_backend_artifact_digest() -> None:
    evidence = replace(pass_evidence(), backend_sha256=None)
    with pytest.raises(ValueError, match="complete admitted digests"):
        ActivationReceipt.from_evidence(evidence)
