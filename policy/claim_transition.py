"""Compatibility shim. Moved to ``weaver_verifier.claim_transition`` (outline step 4)."""

from weaver_verifier.claim_transition import (
    TransitionDecision,
    claim_state_hash,
    validate_transition,
)

__all__ = ["TransitionDecision", "claim_state_hash", "validate_transition"]
