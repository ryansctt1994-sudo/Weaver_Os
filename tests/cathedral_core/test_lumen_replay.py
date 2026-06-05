from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cathedral_core.chronicle.replay import (
    ChronicleEvent,
    replay_lumen_events,
    verify_receipt_state,
)
from cathedral_core.lumen.authority_fsm import AuthorityState


def test_replay_final_state_matches_receipt_state():
    now = datetime.now(timezone.utc)
    proposal_id = "prop_receipt_match_001"

    events = [
        ChronicleEvent(
            event_id="evt_01",
            proposal_id=proposal_id,
            occurred_at=now,
            event_type="PROPOSAL_OPENED",
            payload={},
            prev_hash="GENESIS",
            event_hash="hash_01",
        ),
        ChronicleEvent(
            event_id="evt_02",
            proposal_id=proposal_id,
            occurred_at=now + timedelta(seconds=1),
            event_type="SCOPE_CHECKED",
            payload={
                "actor": "ryan",
                "action": "admit",
                "target": "test_resource",
                "expires_at": now + timedelta(minutes=10),
            },
            prev_hash="hash_01",
            event_hash="hash_02",
        ),
        ChronicleEvent(
            event_id="evt_03",
            proposal_id=proposal_id,
            occurred_at=now + timedelta(seconds=2),
            event_type="AUTHORITY_TRANSITION",
            payload={"requested_state": "NEEDS_REVIEW"},
            prev_hash="hash_02",
            event_hash="hash_03",
        ),
        ChronicleEvent(
            event_id="evt_04",
            proposal_id=proposal_id,
            occurred_at=now + timedelta(seconds=3),
            event_type="AUTHORITY_TRANSITION",
            payload={"requested_state": "ADMITTED"},
            prev_hash="hash_03",
            event_hash="hash_04",
        ),
    ]

    result = replay_lumen_events(events)

    assert result.ok is True
    assert result.events_replayed == 4
    assert result.head_hash == "hash_04"
    assert result.final_states[proposal_id] == AuthorityState.ADMITTED
    assert verify_receipt_state(result, proposal_id, AuthorityState.ADMITTED) is True
    assert verify_receipt_state(result, proposal_id, AuthorityState.EXECUTED) is False


def test_replay_rejects_expired_scope_using_event_time():
    now = datetime.now(timezone.utc)
    proposal_id = "prop_expired_scope_001"

    events = [
        ChronicleEvent(
            event_id="evt_01",
            proposal_id=proposal_id,
            occurred_at=now,
            event_type="PROPOSAL_OPENED",
            payload={},
            prev_hash="GENESIS",
            event_hash="hash_01",
        ),
        ChronicleEvent(
            event_id="evt_02",
            proposal_id=proposal_id,
            occurred_at=now + timedelta(minutes=20),
            event_type="SCOPE_CHECKED",
            payload={
                "actor": "ryan",
                "action": "admit",
                "target": "test_resource",
                "expires_at": now + timedelta(minutes=10),
            },
            prev_hash="hash_01",
            event_hash="hash_02",
        ),
    ]

    result = replay_lumen_events(events)

    assert result.ok is False
    assert result.events_replayed == 2
    assert result.violations[0].code == "SCOPE_REPLAY_DENIED"
    assert result.violations[0].detail == "expired_scope"


def test_replay_rejects_hash_chain_break():
    now = datetime.now(timezone.utc)
    proposal_id = "prop_hash_break_001"

    events = [
        ChronicleEvent(
            event_id="evt_01",
            proposal_id=proposal_id,
            occurred_at=now,
            event_type="PROPOSAL_OPENED",
            payload={},
            prev_hash="GENESIS",
            event_hash="hash_01",
        ),
        ChronicleEvent(
            event_id="evt_02",
            proposal_id=proposal_id,
            occurred_at=now + timedelta(seconds=1),
            event_type="AUTHORITY_TRANSITION",
            payload={"requested_state": "NEEDS_REVIEW"},
            prev_hash="wrong_hash",
            event_hash="hash_02",
        ),
    ]

    result = replay_lumen_events(events)

    assert result.ok is False
    assert result.events_replayed == 2
    assert result.head_hash == "hash_01"
    assert result.violations[0].code == "HASH_CHAIN_BREAK"
