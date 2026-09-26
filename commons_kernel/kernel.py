"""Commons Kernel v0.3 adversarial reference implementation.

Nesting and infrastructure do not imply authority. Only explicit, active grants
authorize protected-state mutations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class Grant:
    grant_id: str
    subject: str
    actions: frozenset[str]
    targets: frozenset[str]
    expires_at: datetime | None = None
    revoked: bool = False

    def active(self, now: datetime) -> bool:
        return not self.revoked and (self.expires_at is None or now < self.expires_at)


@dataclass(frozen=True)
class Proposal:
    actor: str
    action: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    asserted_basis: str = "explicit_grant"


@dataclass(frozen=True)
class Decision:
    verdict: str
    reason: str
    before_hash: str
    after_hash: str
    grant_id: str | None = None


class CommonsKernel:
    """Minimal fail-closed kernel for CK-ADV-001.

    Structural roles are metadata only. They never authorize a mutation.
    """

    def __init__(self, protected_state: dict[str, Any] | None = None) -> None:
        self._state = dict(protected_state or {})
        self._grants: dict[str, Grant] = {}

    @property
    def protected_state(self) -> dict[str, Any]:
        return dict(self._state)

    def add_grant(self, grant: Grant) -> None:
        self._grants[grant.grant_id] = grant

    def state_hash(self) -> str:
        blob = json.dumps(self._state, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def decide(self, proposal: Proposal, now: datetime | None = None) -> Decision:
        now = now or datetime.now(timezone.utc)
        before = self.state_hash()

        eligible = [
            g for g in self._grants.values()
            if g.subject == proposal.actor
            and proposal.action in g.actions
            and proposal.target in g.targets
            and g.active(now)
        ]

        if not eligible:
            after = self.state_hash()
            return Decision("REJECT", "NO_ACTIVE_GRANT", before, after)

        grant = sorted(eligible, key=lambda g: g.grant_id)[0]
        # The grant authorizes only the exact action/target pair. Claimed social,
        # structural, nesting, routing, popularity, or inheritance bases add no power.
        self._apply(proposal)
        after = self.state_hash()
        return Decision("ACCEPT", "EXPLICIT_ACTIVE_GRANT", before, after, grant.grant_id)

    def _apply(self, proposal: Proposal) -> None:
        if proposal.action == "set":
            self._state[proposal.target] = proposal.payload.get("value")
        elif proposal.action == "delete":
            self._state.pop(proposal.target, None)
        else:
            raise ValueError(f"Unsupported protected mutation: {proposal.action}")
