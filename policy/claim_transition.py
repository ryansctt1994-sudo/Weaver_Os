"""Executable transition invariant for bounded claim-state changes.

This module implements a narrow A1 candidate rule:

- a transition certificate binds the exact predecessor claim state;
- a transition certificate binds the exact policy head;
- artifact bindings and supporting evidence are supplied externally and must match;
- scope coverage is checked independently from evidential support;
- exactly one claim-state coordinate may change.

It does not grant authority or define evidence quality.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

_SHA256 = re.compile(r"^[a-f0-9]{64}$")

_REQUIRED_FIELDS = {
    "certificate_id",
    "claim_id",
    "coordinate",
    "predecessor_state_hash",
    "policy_head",
    "proposed_value",
    "artifact_bindings",
    "support_ids",
    "requested_scope",
}
_OPTIONAL_FIELDS = {"limitations"}


@dataclass(frozen=True)
class TransitionDecision:
    accepted: bool
    code: str
    next_state: dict[str, Any] | None = None
    changed_coordinate: str | None = None
    unchanged_coordinates: tuple[str, ...] = ()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def claim_state_hash(state: Mapping[str, Any]) -> str:
    """Hash one exact claim-state value."""
    return hashlib.sha256(_canonical_bytes(dict(state))).hexdigest()


def _reject(code: str) -> TransitionDecision:
    return TransitionDecision(accepted=False, code=code)


def _scope_atoms(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) and item for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return tuple(sorted(value))


def _valid_bindings(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    for name, digest in value.items():
        if not isinstance(name, str) or not name:
            return False
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            return False
    return True


def validate_transition(
    current_state: Mapping[str, Any],
    current_policy_head: str,
    certificate: Mapping[str, Any],
    *,
    admissible_support_ids: Collection[str],
    admissible_scope_atoms: Collection[str],
    expected_artifact_bindings: Mapping[str, str],
) -> TransitionDecision:
    """Validate and derive a one-coordinate successor state.

    Scope coverage and evidential support are deliberately separate inputs.
    Satisfying one cannot substitute for satisfying the other.
    """
    fields = set(certificate)
    missing = sorted(_REQUIRED_FIELDS - fields)
    if missing:
        return _reject("CERTIFICATE_FIELDS_MISSING:" + ",".join(missing))

    extra = sorted(fields - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if extra:
        return _reject("CERTIFICATE_FIELDS_UNRECOGNIZED:" + ",".join(extra))

    predecessor = certificate.get("predecessor_state_hash")
    if not isinstance(predecessor, str) or _SHA256.fullmatch(predecessor) is None:
        return _reject("PREDECESSOR_HASH_INVALID")
    if predecessor != claim_state_hash(current_state):
        return _reject("STALE_PREDECESSOR")

    policy_head = certificate.get("policy_head")
    if not isinstance(policy_head, str) or _SHA256.fullmatch(policy_head) is None:
        return _reject("POLICY_HEAD_INVALID")
    if policy_head != current_policy_head:
        return _reject("POLICY_HEAD_MISMATCH")

    coordinate = certificate.get("coordinate")
    if not isinstance(coordinate, str) or coordinate not in current_state:
        return _reject("COORDINATE_UNKNOWN")

    proposed_value = certificate.get("proposed_value")
    if proposed_value == current_state[coordinate]:
        return _reject("NO_OP_TRANSITION")

    bindings = certificate.get("artifact_bindings")
    if not isinstance(bindings, dict) or not _valid_bindings(bindings):
        return _reject("ARTIFACT_BINDINGS_INVALID")
    if bindings != dict(expected_artifact_bindings):
        return _reject("ARTIFACT_BINDINGS_MISMATCH")

    support_ids = certificate.get("support_ids")
    if (
        not isinstance(support_ids, list)
        or not support_ids
        or not all(isinstance(item, str) and item for item in support_ids)
        or len(support_ids) != len(set(support_ids))
    ):
        return _reject("SUPPORT_IDS_INVALID")

    if not set(support_ids).issubset(set(admissible_support_ids)):
        return _reject("SUPPORT_NOT_ADMISSIBLE")

    requested_scope = _scope_atoms(certificate.get("requested_scope"))
    if requested_scope is None:
        return _reject("REQUESTED_SCOPE_INVALID")

    admissible_scope = set(admissible_scope_atoms)
    if not set(requested_scope).issubset(admissible_scope):
        return _reject("SCOPE_NOT_COVERED")

    if "scope" in current_state:
        current_scope = _scope_atoms(current_state["scope"])
        if current_scope is None:
            return _reject("CURRENT_SCOPE_INVALID")

        if coordinate == "scope":
            proposed_scope = _scope_atoms(proposed_value)
            if proposed_scope is None:
                return _reject("PROPOSED_SCOPE_INVALID")
            if requested_scope != proposed_scope:
                return _reject("SCOPE_TRANSITION_REQUEST_MISMATCH")
        elif requested_scope != current_scope:
            return _reject("SCOPE_DRIFT")

    next_state = dict(current_state)
    next_state[coordinate] = proposed_value
    unchanged = tuple(sorted(key for key in current_state if key != coordinate))

    return TransitionDecision(
        accepted=True,
        code="ACCEPT",
        next_state=next_state,
        changed_coordinate=coordinate,
        unchanged_coordinates=unchanged,
    )
