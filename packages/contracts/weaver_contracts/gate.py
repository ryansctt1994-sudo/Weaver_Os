"""Shapes exchanged with the execution gate: proposals and authorization decisions.

The gate (``weaver_runtime.gate``) takes an authorizer as an injected callable that
returns an ``AuthorizationDecision``. Under UADR-0001 the runtime cannot import the
verifier, so the two agree on these shapes.

This module defines data rules only. It grants no authority and creates no evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .canonical import CanonicalizationError, canonicalize, parse_strict

_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_PLACEHOLDERS = frozenset({"TBD", "TODO", "PENDING", "PLACEHOLDER", "UNKNOWN"})


class GateContractError(ValueError):
    """Raised when a proposal or decision is outside the contract."""


def _identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.match(value) or value.upper() in _PLACEHOLDERS:
        raise GateContractError(f"{name} must be a non-placeholder identifier")
    return value


def _token(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _TOKEN.match(value):
        raise GateContractError(f"{name} must be an UPPER_SNAKE token")
    return value


def _read_only(value: Any) -> Any:
    """Deep read-only view of a parsed WX-CJSON-1 tree: mapping proxies and tuples."""
    if isinstance(value, dict):
        return MappingProxyType({key: _read_only(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_read_only(item) for item in value)
    return value


@dataclass(frozen=True)
class Proposal:
    """What cognition proposes. It carries no authority of its own."""

    proposal_id: str
    actor_id: str
    action: str
    policy_version: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    _payload_bytes: bytes = field(init=False, repr=False, compare=False, default=b"")

    def __post_init__(self) -> None:
        _identifier("proposal_id", self.proposal_id)
        _identifier("actor_id", self.actor_id)
        _token("action", self.action)
        _identifier("policy_version", self.policy_version)
        if not isinstance(self.payload, Mapping):
            raise GateContractError("payload must be an object")
        try:
            canonical = canonicalize(dict(self.payload))
            parsed = parse_strict(canonical)
        except CanonicalizationError as exc:
            raise GateContractError(f"payload is not WX-CJSON-1 canonicalizable: {exc}") from exc
        # The canonical bytes are the payload of record. ``payload`` is a deep read-only
        # view of them: neither the caller's dict nor code holding this proposal (an
        # action, an authorizer) can change what to_dict() reports.
        object.__setattr__(self, "_payload_bytes", canonical)
        object.__setattr__(self, "payload", _read_only(parsed))

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "policy_version": self.policy_version,
            "payload": parse_strict(self._payload_bytes),
        }


@dataclass(frozen=True)
class AuthorizationDecision:
    """An authorizer's answer for one proposal.

    ``valid_until`` is in the gate clock's units (integer seconds by default). An
    allowed decision without a future ``valid_until`` grants nothing.
    """

    allowed: bool
    decision_id: str
    valid_until: int
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise GateContractError("allowed must be a boolean")
        _identifier("decision_id", self.decision_id)
        if (
            not isinstance(self.valid_until, int)
            or isinstance(self.valid_until, bool)
            or self.valid_until < 0
        ):
            raise GateContractError("valid_until must be a non-negative integer")
        if self.allowed and self.reason_code is not None:
            raise GateContractError("an allowed decision must not carry a reason_code")
        if not self.allowed:
            _token("reason_code", self.reason_code)
