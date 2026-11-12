"""WF-001: convert a versioned ZOREL-style ActionOp into a Weaver Proposal.

The adapter performs schema validation and constructs an immutable Proposal
that must pass Weaver's existing contracts. It never creates a grant, signs
a proposal, accesses a ledger, or executes an operation.

authority_required is a declaration only. Only the value "standard" is
accepted; actual permission remains Weaver's signed-grant mechanism.
"""

from __future__ import annotations

from typing import Any

from weaver_contracts.canonical import CanonicalizationError, canonicalize
from weaver_contracts.gate import GateContractError, Proposal

SCHEMA = "WF-ACTION-1"
SUPPORTED_OP = "WRITE_KEY"
SUPPORTED_AUTHORITY = "standard"


class ActionBridgeError(ValueError):
    """Raised when an input is outside the WF-001 contract."""


def _require_exact_keys(obj: dict[str, Any], required: frozenset[str], label: str) -> None:
    if set(obj.keys()) != required:
        raise ActionBridgeError(f"{label} must contain exactly {sorted(required)}")


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ActionBridgeError(f"{name} must be a non-empty string")
    return value


def bridge_action(request: Any) -> Proposal:
    """Convert a WF-ACTION-1 request into a Weaver Proposal.

    The returned Proposal is constructed through Weaver's existing
    validation and canonicalization. Callers cannot mutate it after
    construction. The adapter itself performs no authorization.
    """
    if not isinstance(request, dict):
        raise ActionBridgeError("request must be an object")

    _require_exact_keys(
        request,
        frozenset({"schema", "proposal_id", "policy_version", "action_op"}),
        "request",
    )

    if request["schema"] != SCHEMA:
        raise ActionBridgeError(f"schema must be {SCHEMA!r}")

    proposal_id = _require_str(request["proposal_id"], "proposal_id")
    policy_version = _require_str(request["policy_version"], "policy_version")

    action_op = request["action_op"]
    if not isinstance(action_op, dict):
        raise ActionBridgeError("action_op must be an object")

    _require_exact_keys(
        action_op,
        frozenset({"op_type", "actor", "target", "payload", "authority_required"}),
        "action_op",
    )

    if action_op["op_type"] != SUPPORTED_OP:
        raise ActionBridgeError(f"unsupported op_type: {action_op['op_type']!r}")

    if action_op["authority_required"] != SUPPORTED_AUTHORITY:
        raise ActionBridgeError(
            f"unsupported authority_required: {action_op['authority_required']!r}"
        )

    actor = _require_str(action_op["actor"], "actor")
    target = _require_str(action_op["target"], "target")

    payload = action_op["payload"]
    if not isinstance(payload, dict):
        raise ActionBridgeError("payload must be an object")
    _require_exact_keys(payload, frozenset({"value"}), "payload")
    value = _require_str(payload["value"], "payload.value")

    # Construct through Weaver's Proposal so all identifier, token, and
    # WX-CJSON-1 rules are enforced by the existing contract.
    try:
        proposal = Proposal(
            proposal_id=proposal_id,
            actor_id=actor,
            action=SUPPORTED_OP,
            policy_version=policy_version,
            payload={"key": target, "value": value},
        )
    except GateContractError as exc:
        raise ActionBridgeError(f"proposal rejected by Weaver contract: {exc}") from exc

    # Freeze a canonical copy of the input so later mutation of the caller's
    # dictionaries cannot affect the already-constructed Proposal.
    try:
        canonicalize(request)  # validates the input tree is WX-CJSON-1
    except CanonicalizationError as exc:
        # The Proposal was already built from validated scalars; this is a
        # defensive check only. Non-canonical input should have been rejected
        # by the field checks above.
        raise ActionBridgeError(f"input is not WX-CJSON-1: {exc}") from exc

    return proposal


def proposal_canonical_bytes(proposal: Proposal) -> bytes:
    """Return the WX-CJSON-1 bytes of a bridged Proposal."""
    return canonicalize(proposal.to_dict())
