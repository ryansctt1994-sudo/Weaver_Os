"""Deterministic Chronicle replay adapter for Lumen MVP-0.

This module intentionally stays below Gate L4. It verifies only the MVP-0
sequence required for receipt-backed admission:

Proposal -> Scope -> FSM transition(s) -> replay-derived final state.

It does not evaluate policy hashes, witness signatures, governance debt, or
hardware vetoes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cathedral_core.lumen.authority_fsm import (
    AuthorityState,
    AuthorityTransitionError,
    transition,
)
from cathedral_core.lumen.scope_sovereignty import within_scope

GENESIS_HASH = "GENESIS"


@dataclass(frozen=True)
class ChronicleEvent:
    event_id: str
    proposal_id: str
    occurred_at: datetime
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str


@dataclass(frozen=True)
class ReplayViolation:
    code: str
    detail: str
    event_id: str


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    proposal_id: str | None
    final_states: dict[str, AuthorityState]
    head_hash: str | None
    events_replayed: int
    violations: list[ReplayViolation] = field(default_factory=list)


def replay_lumen_events(events: list[ChronicleEvent]) -> ReplayResult:
    """Replay Lumen MVP-0 authority events as a deterministic reducer.

    The reducer consumes only event-carried data. Scope checks are recomputed
    against ``event.occurred_at`` so replay cannot drift with wall-clock time.
    """

    states: dict[str, AuthorityState] = {}
    violations: list[ReplayViolation] = []
    previous_hash = GENESIS_HASH
    processed = 0

    for event in events:
        processed += 1

        if event.prev_hash != previous_hash:
            violations.append(
                ReplayViolation(
                    code="HASH_CHAIN_BREAK",
                    detail=f"Expected prev_hash {previous_hash}, got {event.prev_hash}",
                    event_id=event.event_id,
                )
            )
            break

        proposal_id = event.proposal_id

        if event.event_type == "PROPOSAL_OPENED":
            states[proposal_id] = AuthorityState.PROPOSAL

        elif event.event_type == "SCOPE_CHECKED":
            decision = within_scope(
                actor=event.payload.get("actor", ""),
                action=event.payload.get("action", ""),
                target=event.payload.get("target", ""),
                expires_at=event.payload.get("expires_at"),
                now=event.occurred_at,
            )
            if not decision.allowed:
                violations.append(
                    ReplayViolation(
                        code="SCOPE_REPLAY_DENIED",
                        detail=decision.reason,
                        event_id=event.event_id,
                    )
                )
                break

        elif event.event_type == "AUTHORITY_TRANSITION":
            current = states.get(proposal_id, AuthorityState.SIMULATION_ONLY)
            try:
                requested = AuthorityState(event.payload["requested_state"])
                states[proposal_id] = transition(current, requested)
            except (KeyError, ValueError, AuthorityTransitionError) as exc:
                violations.append(
                    ReplayViolation(
                        code="ILLEGAL_AUTHORITY_TRANSITION",
                        detail=str(exc),
                        event_id=event.event_id,
                    )
                )
                break

        previous_hash = event.event_hash

    return ReplayResult(
        ok=not violations,
        proposal_id=events[-1].proposal_id if events else None,
        final_states=states,
        head_hash=previous_hash if events else None,
        events_replayed=processed,
        violations=violations,
    )


def verify_receipt_state(
    result: ReplayResult,
    proposal_id: str,
    claimed_state: AuthorityState,
) -> bool:
    """Return true only when a receipt claim matches replay-derived state."""

    return result.ok and result.final_states.get(proposal_id) == claimed_state
