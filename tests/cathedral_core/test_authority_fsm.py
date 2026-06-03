import pytest

from cathedral_core.lumen.authority_fsm import (
    AuthorityState,
    AuthorityTransitionError,
    transition,
)


def test_authority_fsm_allows_canonical_sequence():
    state = AuthorityState.SIMULATION_ONLY
    for next_state in (
        AuthorityState.PROPOSAL,
        AuthorityState.NEEDS_REVIEW,
        AuthorityState.ADMITTED,
        AuthorityState.EXECUTED,
        AuthorityState.OBSERVED,
        AuthorityState.VALUE_ADDED,
    ):
        state = transition(state, next_state)

    assert state == AuthorityState.VALUE_ADDED


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (AuthorityState.PROPOSAL, AuthorityState.EXECUTED),
        (AuthorityState.SIMULATION_ONLY, AuthorityState.ADMITTED),
        (AuthorityState.OBSERVED, AuthorityState.EXECUTED),
        (AuthorityState.VALUE_ADDED, AuthorityState.EXECUTED),
    ],
)
def test_authority_fsm_rejects_illegal_transitions(current, requested):
    with pytest.raises(AuthorityTransitionError):
        transition(current, requested)
