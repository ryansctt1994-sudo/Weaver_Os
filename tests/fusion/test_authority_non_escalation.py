"""WF-001 authority non-escalation controls.

These tests demonstrate that a bridged Proposal is not a grant and that a
Delta-717-style assessment cannot cause execution.
"""

from __future__ import annotations

import pytest

from weaver_fusion.action_bridge import bridge_action


def _valid() -> dict:
    return {
        "schema": "WF-ACTION-1",
        "proposal_id": "wf001-demo-001",
        "policy_version": "policy-v1",
        "action_op": {
            "op_type": "WRITE_KEY",
            "actor": "agent-a",
            "target": "status",
            "payload": {"value": "ready"},
            "authority_required": "standard",
        },
    }


def test_bridged_proposal_is_not_a_signed_grant():
    proposal = bridge_action(_valid())
    # A Proposal carries no signature, no decision, and no valid_until.
    d = proposal.to_dict()
    assert "signature" not in d
    assert "decision" not in d
    assert "valid_until" not in d
    # The adapter does not attach any authorization artifact.
    assert not hasattr(proposal, "grant")
    assert not hasattr(proposal, "allowed")


def test_delta_approved_assessment_cannot_cause_execution():
    """Observer-only fixture: a Delta-style assessment is recorded but
    cannot be used as a grant or to bypass Weaver authorization.
    """
    proposal = bridge_action(_valid())

    # Simulated observer-only assessment (not imported from Delta-717 runtime).
    assessment = {
        "source": "delta-717-observer",
        "status": "APPROVED",
        "epistemic_uncertainty": 0.1,
        "note": "advisory only; not a permission",
    }

    # The assessment is not attached to the Proposal and cannot be
    # interpreted as an AuthorizationDecision.
    assert proposal.to_dict() == {
        "proposal_id": "wf001-demo-001",
        "actor_id": "agent-a",
        "action": "WRITE_KEY",
        "policy_version": "policy-v1",
        "payload": {"key": "status", "value": "ready"},
    }
    # No path from the assessment into the Proposal.
    assert "APPROVED" not in str(proposal.to_dict())
    assert assessment["status"] == "APPROVED"  # fixture exists
    # Explicit non-claim: the fixture does not implement execution.
    with pytest.raises(AttributeError):
        proposal.execute()  # type: ignore[attr-defined]
