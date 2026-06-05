from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cathedral_core.chronicle.replay import ChronicleEvent, replay_lumen_events
from cathedral_core.lumen.authority_fsm import AuthorityState


def test_replay_rejects_proposal_to_executed_skip():
    now = datetime.now(timezone.utc)
    proposal_id = "prop_fail_closed_001"

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
            payload={"requested_state": "EXECUTED"},
            prev_hash="hash_01",
            event_hash="hash_02",
        ),
    ]

    result = replay_lumen_events(events)

    assert result.ok is False
    assert result.events_replayed == 2
    assert len(result.violations) == 1
    assert result.violations[0].code == "ILLEGAL_AUTHORITY_TRANSITION"
    assert "EXECUTED" in result.violations[0].detail
    assert result.final_states[proposal_id] == AuthorityState.PROPOSAL


def test_replay_rejects_missing_actor_scope():
    now = datetime.now(timezone.utc)
    proposal_id = "prop_missing_actor_001"

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
                "actor": "",
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
    assert result.violations[0].detail == "missing_actor"
