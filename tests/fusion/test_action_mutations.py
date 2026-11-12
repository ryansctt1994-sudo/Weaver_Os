"""WF-001 negative controls for schema and mutation."""

from __future__ import annotations

import pytest
from weaver_fusion.action_bridge import ActionBridgeError, bridge_action


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


def test_unsupported_action_type_rejected():
    req = _valid()
    req["action_op"]["op_type"] = "DELETE_KEY"
    with pytest.raises(ActionBridgeError, match="unsupported op_type"):
        bridge_action(req)


def test_extra_input_field_rejected():
    req = _valid()
    req["extra"] = True
    with pytest.raises(ActionBridgeError, match="exactly"):
        bridge_action(req)


def test_missing_input_field_rejected():
    req = _valid()
    del req["proposal_id"]
    with pytest.raises(ActionBridgeError, match="exactly"):
        bridge_action(req)


def test_non_string_identity_rejected():
    req = _valid()
    req["action_op"]["actor"] = 123
    with pytest.raises(ActionBridgeError, match="actor"):
        bridge_action(req)


def test_malformed_payload_rejected():
    req = _valid()
    req["action_op"]["payload"] = {"value": 1}
    with pytest.raises(ActionBridgeError):
        bridge_action(req)


def test_unsupported_authority_declaration_rejected():
    req = _valid()
    req["action_op"]["authority_required"] = "admin"
    with pytest.raises(ActionBridgeError, match="authority_required"):
        bridge_action(req)


def test_non_object_request_rejected():
    with pytest.raises(ActionBridgeError):
        bridge_action(["not", "an", "object"])
