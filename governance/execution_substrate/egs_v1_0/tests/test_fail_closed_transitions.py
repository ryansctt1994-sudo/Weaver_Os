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


def test_happy_path_reaches_released():
    guards = {
        "identity_valid": True,
        "institution_valid": True,
        "token_valid": True,
        "device_attested": True,
        "reagent_attested": True,
        "facility_valid": True,
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
