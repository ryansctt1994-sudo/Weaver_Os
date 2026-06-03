"""Authority finite-state machine for MVP-0.

The FSM encodes the continuous Cathedral sentence as legal transitions.  It is
small by design: illegal skips such as PROPOSAL -> EXECUTED are rejected rather
than interpreted.
"""

from __future__ import annotations

from enum import StrEnum


class AuthorityState(StrEnum):
    SIMULATION_ONLY = "SIMULATION_ONLY"
    PROPOSAL = "PROPOSAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ADMITTED = "ADMITTED"
    EXECUTED = "EXECUTED"
    OBSERVED = "OBSERVED"
    VALUE_ADDED = "VALUE_ADDED"


class AuthorityTransitionError(ValueError):
    """Raised when a requested authority transition is not legal."""


LEGAL_TRANSITIONS: dict[AuthorityState, frozenset[AuthorityState]] = {
    AuthorityState.SIMULATION_ONLY: frozenset({AuthorityState.PROPOSAL}),
    AuthorityState.PROPOSAL: frozenset({AuthorityState.NEEDS_REVIEW}),
    AuthorityState.NEEDS_REVIEW: frozenset({AuthorityState.ADMITTED}),
    AuthorityState.ADMITTED: frozenset({AuthorityState.EXECUTED}),
    AuthorityState.EXECUTED: frozenset({AuthorityState.OBSERVED}),
    AuthorityState.OBSERVED: frozenset({AuthorityState.VALUE_ADDED}),
    AuthorityState.VALUE_ADDED: frozenset(),
}


def transition(current: AuthorityState, requested: AuthorityState) -> AuthorityState:
    """Return ``requested`` if the transition is legal; otherwise fail closed."""

    if requested not in LEGAL_TRANSITIONS[current]:
        raise AuthorityTransitionError(f"Illegal authority transition: {current} -> {requested}")
    return requested
