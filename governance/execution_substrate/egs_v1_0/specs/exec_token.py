"""EGS-TOK-001 context-bound execution token validator.

Defensive governance model only. This module validates authorization context; it does
not perform synthesis or screening.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class TokenContext:
    subject_user: str
    institution: str
    project: str
    facility: str
    device_id: str
    design_digest: str
    reagent_lot: str
    tier: str
    execution_environment: str


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate(token: Mapping[str, Any], ctx: TokenContext, now: datetime | None = None) -> tuple[bool, tuple[str, ...]]:
    """Validate that a token is live and bound to the exact execution context."""
    now = now or datetime.now(timezone.utc)
    failures: list[str] = []

    if token.get("revoked") is True:
        failures.append("revoked")

    try:
        valid_from = _parse_dt(str(token.get("valid_from")))
        valid_until = _parse_dt(str(token.get("valid_until")))
        if not (valid_from <= now <= valid_until):
            failures.append("outside_time_window")
    except Exception:
        failures.append("invalid_time_window")

    expected = {
        "subject_user": ctx.subject_user,
        "institution": ctx.institution,
        "project": ctx.project,
        "facility": ctx.facility,
        "device_id": ctx.device_id,
        "design_digest": ctx.design_digest,
        "reagent_lot": ctx.reagent_lot,
    }
    for field, value in expected.items():
        if token.get(field) != value:
            failures.append(f"mismatch:{field}")

    scope = token.get("scope") or {}
    if scope.get("tier") != ctx.tier:
        failures.append("mismatch:scope.tier")
    if scope.get("execution_environment") != ctx.execution_environment:
        failures.append("mismatch:scope.execution_environment")

    return not failures, tuple(sorted(failures))
