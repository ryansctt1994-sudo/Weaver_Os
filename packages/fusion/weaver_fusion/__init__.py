"""WF-001 typed-action bridge.

Converts one narrowly defined ZOREL-style ActionOp into a Weaver Proposal.
This package grants no authority and performs no execution.
"""

from .action_bridge import ActionBridgeError, bridge_action

__all__ = ["ActionBridgeError", "bridge_action"]
