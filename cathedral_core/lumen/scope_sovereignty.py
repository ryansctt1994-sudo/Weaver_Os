"""Scope sovereignty gate.

Authority is valid only when actor, action, target, and duration are bounded.
This module provides the MVP-0 deterministic shape for that check.  It does not
attempt identity proof or policy lookup yet; those belong in later signed
verifier and registry layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    reason: str


def within_scope(
    actor: str,
    action: str,
    target: str,
    expires_at: Optional[datetime],
) -> ScopeDecision:
    """Validate the four minimum scope-sovereignty fields.

    Scope requires: who acts, what action is requested, what target is affected,
    and when the authority expires.  Missing or expired scope fails closed.
    """

    if not actor.strip():
        return ScopeDecision(False, "missing_actor")
    if not action.strip():
        return ScopeDecision(False, "missing_action")
    if not target.strip():
        return ScopeDecision(False, "missing_target")
    if expires_at is None:
        return ScopeDecision(False, "missing_expiry")

    now = datetime.now(timezone.utc)
    expires = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if expires <= now:
        return ScopeDecision(False, "expired_scope")

    return ScopeDecision(True, "within_scope")
