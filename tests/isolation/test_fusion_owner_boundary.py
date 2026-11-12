"""WF-001 ZOREL/Delta adversarial submissions through the actual V008 owner.

Imported V008 fixture starts a separate owner UID and runs the requester under
its own UID. Run in the root-required V008 workflow: WEAVER_REQUIRE_ISOLATION=1.
These are hosted isolation controls, not an independent external witness.
"""

from __future__ import annotations

import sys

import pytest
from weaver_fusion.action_bridge import bridge_action

from tests.isolation.test_v008_isolated_owner import (
    OTHER_UID,
    REQUESTER_UID,
    live,
    make_grant,
)

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="requires Linux SO_PEERCRED and /proc"
)


def _bridged(*, proposal_id: str = "wf-real-owner-1", actor: str = "agent-a", value: str = "one"):
    return bridge_action(
        {
            "schema": "WF-ACTION-1",
            "proposal_id": proposal_id,
            "policy_version": "policy-v1",
            "action_op": {
                "op_type": "WRITE_KEY",
                "actor": actor,
                "target": "alpha",
                "payload": {"value": value},
                "authority_required": "standard",
            },
        }
    )


def _assert_no_protected_effect(live, response):
    if "reply" in response:
        result = response["reply"]
        assert result.get("status") != "COMMITTED", response
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            assert receipt.get("event_type") != "EXECUTION_COMMITTED", response
    else:
        assert "error" in response, response
    assert live.rows() == {}


def test_zorel_bridged_proposal_without_signed_grant_refused_cross_uid(live):
    proposal = _bridged()
    response = live.submit(REQUESTER_UID, proposal, None)
    _assert_no_protected_effect(live, response)


def test_delta_approved_cannot_replace_signed_grant_cross_uid(live):
    proposal = _bridged()
    advisory = {"source": "delta-717", "status": "APPROVED", "score": 0}
    response = live.submit(REQUESTER_UID, proposal, advisory)
    _assert_no_protected_effect(live, response)


def test_zorel_unsigned_witness_cannot_replace_grant_cross_uid(live):
    proposal = _bridged()
    witness = {"witness_id": "zorel-test", "receipt_hash": "0" * 64, "allowed": True}
    response = live.submit(REQUESTER_UID, proposal, witness)
    _assert_no_protected_effect(live, response)


def test_zorel_grant_for_different_proposal_is_refused_cross_uid(live):
    signed_for = _bridged(proposal_id="wf-signed-for")
    submitted = _bridged(proposal_id="wf-submitted")
    grant = make_grant(live.key, signed_for, grant_id="wf-mismatched-grant")
    response = live.submit(REQUESTER_UID, submitted, grant)
    _assert_no_protected_effect(live, response)


def test_zorel_valid_grant_does_not_override_unlisted_peer_uid(live):
    proposal = _bridged()
    grant = make_grant(live.key, proposal, grant_id="wf-valid-other-uid")
    response = live.submit(OTHER_UID, proposal, grant)
    _assert_no_protected_effect(live, response)


def test_zorel_bridged_valid_signed_grant_commits_as_positive_control(live):
    proposal = _bridged(proposal_id="wf-actual-positive-control")
    grant = make_grant(live.key, proposal, grant_id="wf-actual-positive-grant")
    response = live.submit(REQUESTER_UID, proposal, grant)
    assert "reply" in response, response
    result = response["reply"]
    assert result.get("ok") is True, response
    assert result.get("status") == "COMMITTED", response
    assert result["receipt"]["event_type"] == "EXECUTION_COMMITTED"
    assert result["receipt"]["root"] == "AUTHORITY"
    assert live.rows() == {"alpha": "one"}
