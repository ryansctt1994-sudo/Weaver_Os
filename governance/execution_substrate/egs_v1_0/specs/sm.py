"""EGS-SM-001 fail-closed synthesis state machine.

Defensive governance model only. This module contains no synthesis instructions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Mapping, Tuple


class Outcome(str, Enum):
    ADVANCE = "ADVANCE"
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    FAIL_CLOSED = "FAIL_CLOSED"


class State(str, Enum):
    IDLE = "IDLE"
    AUTHENTICATED = "AUTHENTICATED"
    LOADED = "LOADED"
    SCREENED = "SCREENED"
    ARMED = "ARMED"
    SYNTHESIZING = "SYNTHESIZING"
    VERIFIED = "VERIFIED"
    RELEASED = "RELEASED"
    LOCKOUT = "LOCKOUT"
    NEUTRALIZED = "NEUTRALIZED"
    PURGED = "PURGED"
    SEALED = "SEALED"
    AUDITED = "AUDITED"
    RECERTIFICATION_REQUIRED = "RECERTIFICATION_REQUIRED"


@dataclass(frozen=True)
class Transition:
    to_state: State
    required: FrozenSet[str]
    outcome: Outcome = Outcome.ADVANCE


TRANSITIONS: Mapping[Tuple[State, str], Transition] = {
    (State.IDLE, "AUTHENTICATE"): Transition(State.AUTHENTICATED, frozenset({"identity_valid", "institution_valid"})),
    (State.AUTHENTICATED, "LOAD"): Transition(State.LOADED, frozenset({"token_valid", "device_attested", "reagent_attested", "facility_valid"})),
    (State.LOADED, "SCREEN"): Transition(State.SCREENED, frozenset({"known_hazard_clear", "functional_screen_clear"})),
    (State.SCREENED, "ARM"): Transition(State.ARMED, frozenset({"tier_allowed_for_facility", "quorum_valid", "not_revoked"})),
    (State.ARMED, "COMMIT_SYNTHESIS"): Transition(State.SYNTHESIZING, frozenset({"final_quorum_valid", "chamber_sealed", "audit_sink_available"})),
    (State.SYNTHESIZING, "VERIFY"): Transition(State.VERIFIED, frozenset({"product_verified", "hazard_recheck_clear"})),
    (State.VERIFIED, "RELEASE"): Transition(State.RELEASED, frozenset({"release_authorized", "custody_receipt_written"})),
    (State.LOADED, "ESCALATE"): Transition(State.RECERTIFICATION_REQUIRED, frozenset({"escalation_quorum_required"}), Outcome.ESCALATE),
    (State.SCREENED, "ESCALATE"): Transition(State.RECERTIFICATION_REQUIRED, frozenset({"escalation_quorum_required"}), Outcome.ESCALATE),
    (State.ARMED, "ESCALATE"): Transition(State.RECERTIFICATION_REQUIRED, frozenset({"escalation_quorum_required"}), Outcome.ESCALATE),
}


def step(state: State, event: str, guards: Mapping[str, bool]) -> tuple[State, Outcome, tuple[str, ...]]:
    """Execute one state-machine step.

    A defined transition with missing guards is DENY and does not advance.
    An undefined transition is FAIL_CLOSED and enters LOCKOUT.
    """
    transition = TRANSITIONS.get((state, event))
    if transition is None:
        return State.LOCKOUT, Outcome.FAIL_CLOSED, ("undefined_transition",)

    missing = tuple(sorted(name for name in transition.required if not guards.get(name, False)))
    if missing:
        return state, Outcome.DENY, missing

    return transition.to_state, transition.outcome, ()
