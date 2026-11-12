"""Source-pinned ZOREL and Delta-717 scenarios tested against Weaver's own contracts.

These are behavioral ports, not verbatim upstream test suites and not evidence
of an isolated-owner or independently operated execution boundary.

ZOREL source: abd777e43906cd7bacbd210a5975665730446d2f, tests/test_actionops.py,
tests/test_admissibility.py and tests/test_replay.py.
Delta source: c0a84e44967f9206fecc601acd370b5d7642fa0a,
tests/guide/test_guide.py (Sentinel and ledger adversarial scenarios).
Weaver source: e090726a31490b8f5be9f73bad96280c10709c5a.
"""

from __future__ import annotations

import json

import pytest
from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict
from weaver_contracts.gate import AuthorizationDecision, Proposal
from weaver_fusion.action_bridge import ActionBridgeError, bridge_action, proposal_canonical_bytes
from weaver_runtime.gate import REJECTED, ExecutionGate

from tests.ledger.helpers import open_ledger


def _zorel_style_request(
    *,
    op_type: str = "WRITE_KEY",
    actor: str = "agent-a",
    target: str = "status",
    value: str = "ready",
    authority: str = "standard",
) -> dict:
    """Shape from ZOREL's ActionOp.to_record(), inside the WF-ACTION-1 envelope."""
    return {
        "schema": "WF-ACTION-1",
        "proposal_id": "wf001-source-port-001",
        "policy_version": "policy-v1",
        "action_op": {
            "op_type": op_type,
            "actor": actor,
            "target": target,
            "payload": {"value": value},
            "authority_required": authority,
        },
    }


class _NeverVeto:
    def vetoed(self) -> bool:
        return False


def test_zorel_actionop_record_maps_to_weaver_proposal():
    proposal = bridge_action(_zorel_style_request())
    assert isinstance(proposal, Proposal)
    assert proposal.action == "WRITE_KEY"
    assert proposal.actor_id == "agent-a"
    assert proposal.to_dict()["payload"] == {"key": "status", "value": "ready"}
    assert "signature" not in proposal.to_dict()


@pytest.mark.parametrize("actor", ["", " ", "\t", "TBD"])
def test_zorel_missing_or_placeholder_actor_is_rejected(actor):
    with pytest.raises(ActionBridgeError):
        bridge_action(_zorel_style_request(actor=actor))


@pytest.mark.parametrize("op_type", ["read", "write", "delete", "DELETE_KEY"])
def test_zorel_general_action_types_do_not_expand_weaver_write_scope(op_type):
    with pytest.raises(ActionBridgeError, match="unsupported op_type"):
        bridge_action(_zorel_style_request(op_type=op_type))


def test_zorel_ungranted_admin_declaration_is_refused():
    with pytest.raises(ActionBridgeError, match="authority_required"):
        bridge_action(_zorel_style_request(authority="admin"))


def test_zorel_mutable_caller_record_cannot_change_weaver_proposal():
    request = _zorel_style_request()
    proposal = bridge_action(request)
    baseline = proposal_canonical_bytes(proposal)
    request["action_op"]["payload"]["value"] = "modified"
    request["action_op"]["actor"] = "agent-b"
    assert proposal_canonical_bytes(proposal) == baseline
    assert proposal.actor_id == "agent-a"


def test_zorel_legacy_json_sorting_is_not_weaver_authority_canonicalization():
    """RFC 8785 UTF-16 ordering and ordinary Python Unicode sorting can differ."""
    record = {"\ue000": "bmp", "\U00010000": "supplementary"}
    legacy = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    assert legacy != canonicalize(record)


@pytest.mark.parametrize(
    "bad_document",
    [
        b'{"status":"APPROVED","status":"VETO"}',
        b'{"epistemic_uncertainty":NaN}',
        b'{"epistemic_uncertainty":1e0}',
    ],
)
def test_delta_style_malformed_json_is_refused_by_weaver_intake(bad_document):
    with pytest.raises(CanonicalizationError):
        parse_strict(bad_document)


def test_delta_observer_status_is_not_a_permitted_action_field():
    request = _zorel_style_request()
    request["delta_assessment"] = {"status": "APPROVED"}
    with pytest.raises(ActionBridgeError, match="exactly"):
        bridge_action(request)


@pytest.mark.parametrize("observer_status", ["APPROVED", "VETO", "UNKNOWN"])
def test_delta_observer_verdict_cannot_override_denied_weaver_gate(tmp_path, observer_status):
    """An in-process gate negative control; NOT the isolated-owner acceptance test."""
    observer_assessment = {
        "source": "delta-717",
        "status": observer_status,
        "uncertainty_label": "distributional_dispersion_only",
    }
    proposal = bridge_action(_zorel_style_request())
    executed = []

    def staged(_context):
        executed.append(True)
        return {"staged": True}

    def deny(_proposal):
        return AuthorizationDecision(
            allowed=False,
            decision_id="missing-signed-grant",
            valid_until=2000,
            reason_code="NO_GRANT",
        )

    ledger = open_ledger(tmp_path / "source-port.db")
    try:
        gate = ExecutionGate(
            ledger, veto=_NeverVeto(), authorize=deny, clock=lambda: 1000
        )
        outcome = gate.execute(proposal, staged)
        roots = ledger.snapshot()["roots"]
        assert outcome.status == REJECTED
        assert outcome.reason_code == "NO_GRANT"
        assert executed == []
        assert roots["AUTHORITY"] == []
        assert len(roots["REJECTION"]) == 1
        assert observer_assessment["status"] == observer_status
    finally:
        ledger.close()
