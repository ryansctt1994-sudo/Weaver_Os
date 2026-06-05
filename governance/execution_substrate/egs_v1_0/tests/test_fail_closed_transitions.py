from datetime import datetime, timezone

from governance.execution_substrate.egs_v1_0.specs.exec_token import TokenContext
from governance.execution_substrate.egs_v1_0.specs.sm import Outcome, State, TRANSITIONS, step


EVENTS = [
    "AUTHENTICATE",
    "LOAD",
    "SCREEN",
    "ARM",
    "COMMIT_SYNTHESIS",
    "VERIFY",
    "RELEASE",
    "ESCALATE",
    "FORCE_SYNTHESIS",
]


CTX = TokenContext(
    subject_user="researcher-001",
    institution="example-institution",
    project="approved-project",
    facility="facility-alpha",
    device_id="device-123",
    design_digest="sha256:" + "a" * 64,
    reagent_lot="lot-001",
    tier="T1",
    execution_environment="local",
)


def valid_token():
    return {
        "token_id": "tok-12345678",
        "issuer": "egs-test-ca",
        "subject_user": CTX.subject_user,
        "institution": CTX.institution,
        "project": CTX.project,
        "facility": CTX.facility,
        "device_id": CTX.device_id,
        "design_digest": CTX.design_digest,
        "reagent_lot": CTX.reagent_lot,
        "scope": {"tier": CTX.tier, "max_batch_size": 1, "execution_environment": CTX.execution_environment},
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2027-01-01T00:00:00Z",
        "revoked": False,
    }


def load_guards(token=None):
    return {
        "execution_token": token or valid_token(),
        "token_context": CTX,
        "now": datetime(2026, 6, 4, tzinfo=timezone.utc),
        "device_attested": True,
        "reagent_attested": True,
        "facility_valid": True,
    }


def test_defined_edge_with_missing_guard_denies_without_advancing():
    state, outcome, missing = step(State.IDLE, "AUTHENTICATE", {"identity_valid": True})
    assert state == State.IDLE
    assert outcome == Outcome.DENY
    assert missing == ("institution_valid",)


def test_undefined_edge_fails_closed_into_lockout():
    state, outcome, missing = step(State.IDLE, "COMMIT_SYNTHESIS", {})
    assert state == State.LOCKOUT
    assert outcome == Outcome.FAIL_CLOSED
    assert missing == ("undefined_transition",)


def test_load_uses_computed_token_valid_not_boolean_flag():
    guards = load_guards()
    guards["token_valid"] = False
    state, outcome, missing = step(State.AUTHENTICATED, "LOAD", guards)
    assert state == State.LOADED
    assert outcome == Outcome.ADVANCE
    assert not missing


def test_forged_token_denies_at_load():
    forged = valid_token()
    forged["device_id"] = "forged-device"
    guards = load_guards(forged)
    guards["token_valid"] = True
    state, outcome, missing = step(State.AUTHENTICATED, "LOAD", guards)
    assert state == State.AUTHENTICATED
    assert outcome == Outcome.DENY
    assert "computed_token_valid" in missing


def test_happy_path_reaches_released():
    guards = {
        "identity_valid": True,
        "institution_valid": True,
        **load_guards(),
        "known_hazard_clear": True,
        "functional_screen_clear": True,
        "tier_allowed_for_facility": True,
        "quorum_valid": True,
        "not_revoked": True,
        "final_quorum_valid": True,
        "chamber_sealed": True,
        "audit_sink_available": True,
        "product_verified": True,
        "hazard_recheck_clear": True,
        "release_authorized": True,
        "custody_receipt_written": True,
    }
    state = State.IDLE
    for event in ["AUTHENTICATE", "LOAD", "SCREEN", "ARM", "COMMIT_SYNTHESIS", "VERIFY", "RELEASE"]:
        state, outcome, missing = step(state, event, guards)
        assert outcome == Outcome.ADVANCE
        assert not missing
    assert state == State.RELEASED


def test_every_undefined_pair_fails_closed():
    for state in State:
        for event in EVENTS:
            if (state, event) in TRANSITIONS:
                continue
            next_state, outcome, _ = step(state, event, {})
            assert next_state == State.LOCKOUT
            assert outcome == Outcome.FAIL_CLOSED


def test_matter_commit_requires_all_commit_guards():
    incomplete = {"final_quorum_valid": True, "chamber_sealed": True}
    state, outcome, missing = step(State.ARMED, "COMMIT_SYNTHESIS", incomplete)
    assert state == State.ARMED
    assert outcome == Outcome.DENY
    assert "audit_sink_available" in missing


def test_no_undefined_edge_can_enter_synthesizing():
    for state in State:
        for event in EVENTS:
            if (state, event) == (State.ARMED, "COMMIT_SYNTHESIS"):
                continue
            next_state, outcome, _ = step(state, event, {})
            assert next_state != State.SYNTHESIZING
