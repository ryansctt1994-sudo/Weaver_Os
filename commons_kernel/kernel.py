"""Commons Kernel v0.3 adversarial reference implementation.

CK-ADV-002 closes the naked add_grant bootstrap path. Authority can enter the
live grant set only through sealed bootstrap construction, valid attenuated
minting, or an explicitly unsafe test seam.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any


class MintBasis(str, Enum):
    ROOT_BOOTSTRAP = "ROOT_BOOTSTRAP"
    EXPLICIT_GRANT = "EXPLICIT_GRANT"
    ATTENUATED_DELEGATION = "ATTENUATED_DELEGATION"


@dataclass(frozen=True)
class Grant:
    grant_id: str
    grantor: str
    subject: str
    actions: frozenset[str]
    targets: frozenset[str]
    issued_at: datetime
    expires_at: datetime | None
    revoked: bool = False
    parent_grant_id: str | None = None
    mint_basis: MintBasis = MintBasis.EXPLICIT_GRANT

    def active(self, now: datetime) -> bool:
        return (
            not self.revoked
            and self.issued_at <= now
            and (self.expires_at is None or now < self.expires_at)
        )


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
    before_grant_hash: str | None = None
    after_grant_hash: str | None = None


class CommonsKernel:
    def __init__(
        self,
        protected_state: dict[str, Any] | None = None,
        *,
        bootstrap_grant: Grant | None = None,
    ) -> None:
        self._state = dict(protected_state or {})
        self._grants: dict[str, Grant] = {}
        if bootstrap_grant is not None:
            if bootstrap_grant.mint_basis is not MintBasis.ROOT_BOOTSTRAP:
                raise ValueError("bootstrap grant must use ROOT_BOOTSTRAP")
            if bootstrap_grant.expires_at is None:
                raise ValueError("bootstrap grant must have hard expiry")
            self._grants[bootstrap_grant.grant_id] = bootstrap_grant

    @property
    def protected_state(self) -> dict[str, Any]:
        return dict(self._state)

    def add_grant(self, grant: Grant) -> Decision:
        """Former production back door: retained only to fail closed."""
        before = self.state_hash()
        grants_before = self.grant_set_hash()
        return Decision(
            "REJECT",
            "NO_GRANT_PROVENANCE",
            before,
            before,
            before_grant_hash=grants_before,
            after_grant_hash=grants_before,
        )

    def unsafe_test_inject(self, grant: Grant) -> None:
        """Test-only seam. Production callers must never use this."""
        self._grants[grant.grant_id] = grant

    def state_hash(self) -> str:
        blob = json.dumps(self._state, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def grant_set_hash(self) -> str:
        rows = [
            {
                "grant_id": g.grant_id,
                "grantor": g.grantor,
                "subject": g.subject,
                "actions": sorted(g.actions),
                "targets": sorted(g.targets),
                "issued_at": g.issued_at.isoformat(),
                "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                "revoked": g.revoked,
                "parent_grant_id": g.parent_grant_id,
                "mint_basis": g.mint_basis.value,
            }
            for g in sorted(self._grants.values(), key=lambda x: x.grant_id)
        ]
        blob = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def propose_mint(self, actor: str, new_grant: Grant, now: datetime | None = None) -> Decision:
        now = now or datetime.now(timezone.utc)
        before = self.state_hash()
        grants_before = self.grant_set_hash()

        if new_grant.mint_basis is MintBasis.ROOT_BOOTSTRAP:
            return self._mint_reject("NO_GRANT_PROVENANCE", before, grants_before)

        parent = self._grants.get(new_grant.parent_grant_id or "")
        if parent is None:
            return self._mint_reject("NO_GRANT_PROVENANCE", before, grants_before)
        if not parent.active(now):
            reason = "BOOTSTRAP_EXPIRED" if parent.mint_basis is MintBasis.ROOT_BOOTSTRAP else "ACTOR_CANNOT_MINT"
            return self._mint_reject(reason, before, grants_before)
        if parent.subject != actor or "mint" not in parent.actions:
            return self._mint_reject("ACTOR_CANNOT_MINT", before, grants_before)
        if new_grant.grantor != actor:
            return self._mint_reject("NO_GRANT_PROVENANCE", before, grants_before)

        child_actions = new_grant.actions - {"mint"}
        parent_actions = parent.actions - {"mint"}
        if not child_actions.issubset(parent_actions) or not new_grant.targets.issubset(parent.targets):
            return self._mint_reject("DELEGATION_EXPANDS_AUTHORITY", before, grants_before)

        if new_grant.expires_at is None or (
            parent.expires_at is not None and new_grant.expires_at > parent.expires_at
        ):
            return self._mint_reject("DELEGATION_EXPANDS_AUTHORITY", before, grants_before)

        if "emergency" in parent.actions and new_grant.mint_basis is not MintBasis.ATTENUATED_DELEGATION:
            return self._mint_reject("EMERGENCY_CANNOT_MINT_STANDING", before, grants_before)

        self._grants[new_grant.grant_id] = new_grant
        grants_after = self.grant_set_hash()
        return Decision(
            "ACCEPT", "VALID_GRANT_PROVENANCE", before, before, new_grant.grant_id,
            grants_before, grants_after,
        )

    def decide(self, proposal: Proposal, now: datetime | None = None) -> Decision:
        now = now or datetime.now(timezone.utc)
        before = self.state_hash()
        grants_before = self.grant_set_hash()
        eligible = [
            g for g in self._grants.values()
            if g.subject == proposal.actor
            and proposal.action in g.actions
            and proposal.target in g.targets
            and g.active(now)
        ]
        if not eligible:
            return Decision(
                "REJECT", "NO_ACTIVE_GRANT", before, before,
                before_grant_hash=grants_before, after_grant_hash=grants_before,
            )
        grant = sorted(eligible, key=lambda g: g.grant_id)[0]
        self._apply(proposal)
        after = self.state_hash()
        return Decision(
            "ACCEPT", "EXPLICIT_ACTIVE_GRANT", before, after, grant.grant_id,
            grants_before, grants_before,
        )

    def _mint_reject(self, reason: str, before: str, grants_before: str) -> Decision:
        return Decision(
            "REJECT", reason, before, before,
            before_grant_hash=grants_before, after_grant_hash=grants_before,
        )

    def _apply(self, proposal: Proposal) -> None:
        if proposal.action == "set":
            self._state[proposal.target] = proposal.payload.get("value")
        elif proposal.action == "delete":
            self._state.pop(proposal.target, None)
        else:
            raise ValueError(f"Unsupported protected mutation: {proposal.action}")
