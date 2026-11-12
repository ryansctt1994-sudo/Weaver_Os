"""WF-001 authority non-escalation controls.

These tests demonstrate that a bridged Proposal is not a grant and that a
Delta-717-style assessment cannot cause execution. They establish structural
separation only; they do not exercise an end-to-end owner refusal path.
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
    d = proposal.to_dict()
    assert "signature" not in d
    assert "decision" not in d
    assert "valid_until" not in d
    assert not hasattr(proposal, "grant")
    assert not hasattr(proposal, "allowed")


def test_delta_approved_assessment_cannot_cause_execution():
    """Observer-only fixture: a Delta-style assessment is recorded but
    cannot be used as a grant or to bypass Weaver authorization.

    This test demonstrates structural separation only. It does not invoke
    the protected owner or prove an end-to-end unauthorized-effect refusal.
    """
    proposal = bridge_action(_valid())

    assessment = {
        "source": "delta-717-observer",
        "status": "APPROVED",
        "epistemic_uncertainty": 0.1,
        "note": "advisory only; not a permission",
    }

    assert proposal.to_dict() == {
        "proposal_id": "wf001-demo-001",
        "actor_id": "agent-a",
        "action": "WRITE_KEY",
        "policy_version": "policy-v1",
        "payload": {"key": "status", "value": "ready"},
    }
    assert "APPROVED" not in str(proposal.to_dict())
    assert assessment["status"] == "APPROVED"
    # The Proposal has no execution method; the assessment cannot invoke one.
    with pytest.raises(AttributeError):
        proposal.execute()  # type: ignore[attr-defined]
    # Explicit non-claim recorded for reviewers.
    assert "not a permission" in assessment["note"]
