from __future__ import annotations

import copy

from policy.claim_transition import claim_state_hash, validate_transition

POLICY_HEAD = "b" * 64
BINDINGS = {"source": "a" * 64}
SUPPORT = {"receipt-mechanics", "receipt-repro", "receipt-scope"}
COVERAGE = {"workload-A", "host-linux"}


def state():
    return {
        "binding": "artifact-set-001",
        "mechanics": "UNQUALIFIED",
        "scientific_result": "NOT_ESTABLISHED",
        "reproduction": "LOCAL_ONLY",
        "scope": ["workload-A"],
        "authority": "O0_WITHHELD",
    }


def certificate(current, coordinate, proposed_value, support_id, requested_scope=None):
    return {
        "certificate_id": "TC-001",
        "claim_id": "ELPIS-DSAG-001",
        "coordinate": coordinate,
        "predecessor_state_hash": claim_state_hash(current),
        "policy_head": POLICY_HEAD,
        "proposed_value": proposed_value,
        "artifact_bindings": dict(BINDINGS),
        "support_ids": [support_id],
        "requested_scope": requested_scope or ["workload-A"],
        "limitations": ["bounded fixture"],
    }


def decide(current, cert, *, support=SUPPORT, coverage=COVERAGE):
    return validate_transition(
        current,
        POLICY_HEAD,
        cert,
        admissible_support_ids=support,
        admissible_scope_atoms=coverage,
        expected_artifact_bindings=BINDINGS,
    )


def test_mechanics_transition_cannot_touch_scientific_result():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    decision = decide(current, cert)

    assert decision.accepted
    assert decision.next_state is not None
    assert decision.next_state["mechanics"] == "LOCAL_QUALIFIED"
    assert decision.next_state["scientific_result"] == "NOT_ESTABLISHED"
    assert decision.next_state["reproduction"] == "LOCAL_ONLY"
    assert decision.next_state["scope"] == ["workload-A"]
    assert decision.next_state["authority"] == "O0_WITHHELD"


def test_stale_predecessor_is_rejected():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    changed = copy.deepcopy(current)
    changed["binding"] = "artifact-set-002"

    decision = decide(changed, cert)
    assert not decision.accepted
    assert decision.code == "STALE_PREDECESSOR"


def test_policy_head_mismatch_is_rejected():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    decision = validate_transition(
        current,
        "c" * 64,
        cert,
        admissible_support_ids=SUPPORT,
        admissible_scope_atoms=COVERAGE,
        expected_artifact_bindings=BINDINGS,
    )
    assert not decision.accepted
    assert decision.code == "POLICY_HEAD_MISMATCH"


def test_scope_coverage_does_not_substitute_for_support():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    decision = decide(current, cert, support=set())
    assert not decision.accepted
    assert decision.code == "SUPPORT_NOT_ADMISSIBLE"


def test_support_does_not_substitute_for_scope_coverage():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    decision = decide(current, cert, coverage=set())
    assert not decision.accepted
    assert decision.code == "SCOPE_NOT_COVERED"


def test_reproduction_transition_cannot_broaden_scope_implicitly():
    current = state()
    cert = certificate(
        current,
        "reproduction",
        "CROSS_HOST_SAME_OPERATOR",
        "receipt-repro",
        requested_scope=["workload-A", "host-linux"],
    )
    decision = decide(current, cert)
    assert not decision.accepted
    assert decision.code == "SCOPE_DRIFT"


def test_scope_transition_requires_coverage_of_proposed_scope():
    current = state()
    cert = certificate(
        current,
        "scope",
        ["workload-A", "host-linux"],
        "receipt-scope",
        requested_scope=["workload-A", "host-linux"],
    )
    decision = decide(current, cert)
    assert decision.accepted
    assert decision.next_state is not None
    assert decision.next_state["scope"] == ["workload-A", "host-linux"]
    assert decision.next_state["scientific_result"] == "NOT_ESTABLISHED"


def test_artifact_binding_mismatch_is_rejected():
    current = state()
    cert = certificate(
        current,
        "mechanics",
        "LOCAL_QUALIFIED",
        "receipt-mechanics",
    )
    decision = validate_transition(
        current,
        POLICY_HEAD,
        cert,
        admissible_support_ids=SUPPORT,
        admissible_scope_atoms=COVERAGE,
        expected_artifact_bindings={"source": "d" * 64},
    )
    assert not decision.accepted
    assert decision.code == "ARTIFACT_BINDINGS_MISMATCH"
