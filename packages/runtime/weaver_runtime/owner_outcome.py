"""WEAVER-V008 crash-recovery slice: what durable history says about one proposal id.

Research-only. ``lookup_outcome`` reads a ledger snapshot and answers one question: what
happened to proposal ``X``? It uses only what the gate already records. Every attempt
writes one receipt, the commit event and every refusal event embed the canonical proposal,
and a commit claims ``EXECUTION_COMMITTED:<proposal_id>`` as a unique key inside the commit
transaction. Nothing here writes.

Statuses:

* ``COMMITTED``: a commit is durably recorded. Final. ``receipt`` is that commit's receipt,
  so the same receipt comes back on every retry and after every restart.
* ``REFUSED``: one or more attempts were durably refused and nothing committed. NOT final:
  refusals claim no unique key, so a later attempt (for example with a fresh grant) may still
  commit. ``receipt`` is the latest refusal.
* ``UNKNOWN``: no durable record for this id. The owner never received it, or died before the
  commit transaction completed (which rolls back). It is not a refusal, and a request still
  queued at the owner may yet commit. Retrying the same proposal is safe: the unique key
  allows at most one commit.
* ``CONFLICT`` (computed by callers that know the submitted proposal): the id is committed,
  but for different proposal content. Final, and never to be reported as this proposal's
  commit.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict

COMMITTED = "COMMITTED"
REFUSED = "REFUSED"
UNKNOWN = "UNKNOWN"
CONFLICT = "CONFLICT"

_COMMIT_EVENT = "EXECUTION_COMMITTED"
_REFUSAL_EVENTS = frozenset({"EXECUTION_REFUSED", "EXECUTION_ABORTED"})


class OutcomeError(Exception):
    """The ledger contradicts the one-commit-per-proposal invariant or is unreadable."""


def proposal_digest(proposal: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical proposal; the same value a grant's proposal_sha256 binds."""
    return hashlib.sha256(canonicalize(dict(proposal))).hexdigest()


def _proposal_of(entry: Mapping[str, Any]) -> dict[str, Any] | None:
    try:
        event = parse_strict(str(entry["event"]).encode("utf-8"))
    except (CanonicalizationError, KeyError) as exc:
        raise OutcomeError(f"unreadable ledger event: {exc}") from exc
    proposal = event.get("proposal") if isinstance(event, dict) else None
    return proposal if isinstance(proposal, dict) else None


def lookup_outcome(snapshot: Mapping[str, Any], proposal_id: str) -> dict[str, Any]:
    roots = snapshot["roots"]
    commits: list[tuple[dict[str, Any], dict[str, Any]]] = []
    refusals: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for root, wanted, bucket in (
        ("AUTHORITY", frozenset({_COMMIT_EVENT}), commits),
        ("REJECTION", _REFUSAL_EVENTS, refusals),
    ):
        for entry in roots[root]:
            if entry["receipt"].get("event_type") not in wanted:
                continue
            proposal = _proposal_of(entry)
            if proposal is not None and proposal.get("proposal_id") == proposal_id:
                bucket.append((proposal, dict(entry["receipt"])))
    if len(commits) > 1:
        raise OutcomeError(f"ledger holds {len(commits)} commits for {proposal_id!r}")
    if commits:
        proposal, receipt = commits[0]
        return {
            "status": COMMITTED,
            "final": True,
            "proposal_id": proposal_id,
            "actor_id": proposal.get("actor_id"),
            "proposal_sha256": proposal_digest(proposal),
            "receipt": receipt,
            "refused_attempts": len(refusals),
        }
    if refusals:
        proposal, receipt = refusals[-1]
        return {
            "status": REFUSED,
            "final": False,
            "proposal_id": proposal_id,
            "actor_id": proposal.get("actor_id"),
            "proposal_sha256": proposal_digest(proposal),
            "receipt": receipt,
            "refused_attempts": len(refusals),
        }
    return {
        "status": UNKNOWN,
        "final": False,
        "proposal_id": proposal_id,
        "actor_id": None,
        "proposal_sha256": None,
        "receipt": None,
        "refused_attempts": 0,
    }


def conflict(proposal_id: str) -> dict[str, Any]:
    """The id committed with different content. No receipt: it is not this proposal's."""
    return {
        "status": CONFLICT,
        "final": True,
        "proposal_id": proposal_id,
        "actor_id": None,
        "proposal_sha256": None,
        "receipt": None,
        "refused_attempts": None,
    }
