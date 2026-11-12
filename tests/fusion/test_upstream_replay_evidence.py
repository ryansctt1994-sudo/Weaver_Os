"""ZOREL/Delta-origin replay challenges against Weaver's real ledger and verifier.

These are behaviorally translated controls, not upstream code imports.
ZOREL: abd777e43906cd7bacbd210a5975665730446d2f, tests/test_replay.py
and tests/test_witness.py.
Delta: c0a84e44967f9206fecc601acd370b5d7642fa0a,
tests/guide/test_guide.py (tamper, truncation, snapshot and rollback scenarios).

Historical proof boundaries: an unanchored chain does NOT authenticate history.
"""

from __future__ import annotations

import copy

import pytest
from weaver_contracts.canonical import CanonicalizationError, parse_strict, sha256_hex
from weaver_fusion.action_bridge import ActionBridgeError, bridge_action
from weaver_runtime.ledger import AdmissionError
from weaver_verifier.ledger import verify_snapshot

from tests.ledger.helpers import open_ledger


def _request() -> dict:
    return {
        "schema": "WF-ACTION-1",
        "proposal_id": "wf-source-evidence",
        "policy_version": "policy-v1",
        "action_op": {
            "op_type": "WRITE_KEY",
            "actor": "agent-a",
            "target": "alpha",
            "payload": {"value": "one"},
            "authority_required": "standard",
        },
    }


def _three_events(ledger) -> None:
    for index in range(3):
        ledger.admit(
            "TEST_EVENT",
            {"step": index, "provenance": "delta-717-test-scenario"},
            actor_id="test-agent",
            policy_version="policy-v1",
        )


def test_zorel_unsigned_witness_record_cannot_be_accepted_as_authorization():
    request = _request()
    proposal = bridge_action(request)
    request["witness"] = {
        "witness_id": "reference-only",
        "receipt_hash": sha256_hex(proposal.to_dict()),
        "decision": {"allowed": True},
    }
    with pytest.raises(ActionBridgeError, match="exactly"):
        bridge_action(request)


def test_zorel_replay_digest_stable_under_mapping_reorder():
    proposal = bridge_action(_request()).to_dict()
    assert sha256_hex(proposal) == sha256_hex(dict(reversed(list(proposal.items()))))


@pytest.mark.parametrize(
    "malformed",
    [
        b'{"outer":{"status":"APPROVED","status":"VETO"}}',
        b'{"status":"APPROVED","confidence":NaN}',
        b'{"status":"APPROVED","confidence":Infinity}',
        b'{"status":"APPROVED","confidence":1.0}',
    ],
    ids=["nested-duplicate", "nan", "infinity", "float"],
)
def test_delta_observer_json_must_pass_real_weaver_canonical_reader(malformed):
    with pytest.raises(CanonicalizationError):
        parse_strict(malformed)


@pytest.mark.parametrize(
    "mutation",
    ["edit", "delete-middle", "reorder", "duplicate", "insert", "truncate", "root-swap"],
)
def test_delta_ledger_tamper_scenarios_fail_weaver_anchored_verification(tmp_path, mutation):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        _three_events(ledger)
        untouched = ledger.snapshot()
        candidate = copy.deepcopy(untouched)
        anchor = ledger.anchor().to_dict()
        assert verify_snapshot(untouched, anchor=anchor).ok
        events = candidate["roots"]["AUTHORITY"]
        if mutation == "edit":
            events[1]["event"] = '{"step":999}'
        elif mutation == "delete-middle":
            events.pop(1)
        elif mutation == "reorder":
            events[0], events[1] = events[1], events[0]
        elif mutation == "duplicate":
            events.insert(1, copy.deepcopy(events[0]))
        elif mutation == "insert":
            events.append(copy.deepcopy(events[-1]))
        elif mutation == "truncate":
            events.pop()
        else:
            candidate["roots"]["REJECTION"].append(events.pop())
        assert not verify_snapshot(candidate, anchor=anchor).ok, mutation
        assert ledger.snapshot() == untouched


def test_delta_unsigned_tail_truncation_needs_external_anchor(tmp_path):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        _three_events(ledger)
        anchor = ledger.anchor().to_dict()
        truncated = ledger.snapshot()
        truncated["roots"]["AUTHORITY"].pop()
        unanchored = verify_snapshot(truncated)
        assert unanchored.ok
        assert not unanchored.anchored
        assert not verify_snapshot(truncated, anchor=anchor).ok


def test_delta_full_history_rewrite_is_not_independently_authenticated(tmp_path):
    with open_ledger(tmp_path / "first.db") as original:
        _three_events(original)
        anchor = original.anchor().to_dict()
        assert verify_snapshot(original.snapshot(), anchor=anchor).ok
    with open_ledger(tmp_path / "alternate.db") as alternate:
        for index in range(3):
            alternate.admit(
                "TEST_EVENT",
                {"step": index, "provenance": "rewritten-history"},
                actor_id="test-agent",
                policy_version="policy-v1",
            )
        assert verify_snapshot(alternate.snapshot()).ok
        assert not verify_snapshot(alternate.snapshot(), anchor=anchor).ok


@pytest.mark.parametrize(
    "bad_value",
    [float("nan"), float("inf"), float("-inf"), 2**54],
    ids=["nan", "positive-infinity", "negative-infinity", "unsafe-integer"],
)
def test_delta_invalid_numeric_event_cannot_advance_weaver_ledger(tmp_path, bad_value):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        _three_events(ledger)
        before = ledger.snapshot()
        old_anchor = ledger.anchor()
        with pytest.raises(AdmissionError):
            ledger.admit(
                "TEST_EVENT",
                {"value": bad_value},
                actor_id="test-agent",
                policy_version="policy-v1",
            )
        assert ledger.snapshot() == before
        assert ledger.anchor() == old_anchor


def test_delta_simulated_atomic_append_failure_rolls_back(tmp_path, monkeypatch):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        _three_events(ledger)
        before = ledger.snapshot()

        def interrupted(_receipt):
            raise RuntimeError("simulated interrupted append")

        with monkeypatch.context() as patch:
            patch.setattr(ledger, "_advance_head", interrupted)
            with pytest.raises(RuntimeError, match="interrupted"):
                ledger.admit(
                    "TEST_EVENT",
                    {"step": 99},
                    actor_id="test-agent",
                    policy_version="policy-v1",
                )
        assert ledger.snapshot() == before
        assert verify_snapshot(ledger.snapshot(), anchor=ledger.anchor().to_dict()).ok
