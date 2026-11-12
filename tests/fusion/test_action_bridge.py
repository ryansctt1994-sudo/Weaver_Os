"""WF-001 contract tests for the typed-action bridge."""

from __future__ import annotations

import copy

import pytest

from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import Proposal

from weaver_fusion.action_bridge import ActionBridgeError, bridge_action, proposal_canonical_bytes


def _valid_request() -> dict:
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


def test_valid_request_produces_expected_proposal():
    proposal = bridge_action(_valid_request())
    assert isinstance(proposal, Proposal)
    assert proposal.to_dict() == {
        "proposal_id": "wf001-demo-001",
        "actor_id": "agent-a",
        "action": "WRITE_KEY",
        "policy_version": "policy-v1",
        "payload": {"key": "status", "value": "ready"},
    }


def test_output_is_wx_cjson_1_canonicalizable():
    proposal = bridge_action(_valid_request())
    # Round-trip through Weaver's own canonicalization must succeed.
    raw = proposal_canonical_bytes(proposal)
    assert canonicalize(proposal.to_dict()) == raw


def test_mutable_input_cannot_change_constructed_proposal():
    request = _valid_request()
    proposal = bridge_action(request)
    request["action_op"]["payload"]["value"] = "tampered"
    request["action_op"]["actor"] = "other"
    assert proposal.to_dict()["payload"]["value"] == "ready"
    assert proposal.to_dict()["actor_id"] == "agent-a"


def test_equivalent_encodings_produce_identical_canonical_bytes():
    a = bridge_action(_valid_request())
    # Different key order in the payload dict.
    request_b = _valid_request()
    request_b["action_op"]["payload"] = {"value": "ready"}  # already single key
    b = bridge_action(request_b)
    assert proposal_canonical_bytes(a) == proposal_canonical_bytes(b)


def test_changing_actor_changes_canonical_digest():
    base = proposal_canonical_bytes(bridge_action(_valid_request()))
    mutated = _valid_request()
    mutated["action_op"]["actor"] = "agent-b"
    assert proposal_canonical_bytes(bridge_action(mutated)) != base


def test_changing_target_changes_canonical_digest():
    base = proposal_canonical_bytes(bridge_action(_valid_request()))
    mutated = _valid_request()
    mutated["action_op"]["target"] = "other"
    assert proposal_canonical_bytes(bridge_action(mutated)) != base


def test_changing_value_changes_canonical_digest():
    base = proposal_canonical_bytes(bridge_action(_valid_request()))
    mutated = _valid_request()
    mutated["action_op"]["payload"]["value"] = "other"
    assert proposal_canonical_bytes(bridge_action(mutated)) != base


def test_changing_policy_version_changes_canonical_digest():
    base = proposal_canonical_bytes(bridge_action(_valid_request()))
    mutated = _valid_request()
    mutated["policy_version"] = "policy-v2"
    assert proposal_canonical_bytes(bridge_action(mutated)) != base
