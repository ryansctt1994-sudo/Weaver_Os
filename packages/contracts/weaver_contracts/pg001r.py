"""Canonical contracts for the PG-001R clean-room promotion gate.

This module defines data only. It performs strict parsing and validation but does
not decide promotion, issue authority, mutate state, or create evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when a promotion request violates the frozen input contract."""


class EvidenceLevel(IntEnum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6

    @classmethod
    def parse(cls, value: object) -> "EvidenceLevel":
        if not isinstance(value, str):
            raise ContractError("evidence levels must be strings")
        try:
            return cls[value]
        except KeyError as exc:
            raise ContractError(f"unknown evidence level: {value!r}") from exc


class AuthorityLevel(IntEnum):
    NONE = 0
    RESEARCH = 1
    INTERNAL = 2
    PILOT = 3
    PRODUCTION = 4

    @classmethod
    def parse(cls, value: object) -> "AuthorityLevel":
        if not isinstance(value, str):
            raise ContractError("authority levels must be strings")
        try:
            return cls[value]
        except KeyError as exc:
            raise ContractError(f"unknown authority level: {value!r}") from exc


AUTHORITY_EVIDENCE_FLOOR: dict[AuthorityLevel, EvidenceLevel] = {
    AuthorityLevel.NONE: EvidenceLevel.R0,
    AuthorityLevel.RESEARCH: EvidenceLevel.R1,
    AuthorityLevel.INTERNAL: EvidenceLevel.R2,
    AuthorityLevel.PILOT: EvidenceLevel.R4,
    AuthorityLevel.PRODUCTION: EvidenceLevel.R6,
}

_ALLOWED_FIELDS = {
    "artifact_id",
    "current_evidence_level",
    "verified_evidence_level",
    "requested_evidence_level",
    "requested_authority",
    "required_evidence",
    "verified_evidence",
    "recorded_evidence",
    "open_contradictions",
    "recovery_dependencies_required",
    "recovery_dependencies_present",
    "self_issued_receipt_only",
    "independent_reproduction_receipts",
    "external_publication_claimed_as_evidence",
    "external_publication_receipt_bound",
    "governance_bundle_id",
    "gate_decision_id",
    "human_authority_id",
    "clinical_scope",
    "clinical_safety_level",
}


def _require_nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    result = value.strip()
    if result.upper() in {"TBD", "TODO", "PLACEHOLDER", "UNKNOWN", "NONE"}:
        raise ContractError(f"{field} may not be a placeholder")
    return result


def _optional_identifier(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_nonempty_string(value, field)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError(f"{field} must be a JSON array of strings")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ContractError(f"{field}[{index}] must be a non-empty string")
        normalized = item.strip()
        if normalized in seen:
            raise ContractError(f"{field} contains duplicate value {normalized!r}")
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)


def _strict_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f"{field} must be a boolean")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class PromotionRequest:
    artifact_id: str
    current_evidence_level: EvidenceLevel
    verified_evidence_level: EvidenceLevel
    requested_evidence_level: EvidenceLevel
    requested_authority: AuthorityLevel
    required_evidence: tuple[str, ...]
    verified_evidence: tuple[str, ...]
    recorded_evidence: tuple[str, ...]
    open_contradictions: tuple[str, ...]
    recovery_dependencies_required: tuple[str, ...]
    recovery_dependencies_present: tuple[str, ...]
    self_issued_receipt_only: bool
    independent_reproduction_receipts: int
    external_publication_claimed_as_evidence: bool
    external_publication_receipt_bound: bool
    governance_bundle_id: str | None
    gate_decision_id: str | None
    human_authority_id: str | None
    clinical_scope: bool
    clinical_safety_level: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PromotionRequest":
        if not isinstance(payload, Mapping):
            raise ContractError("promotion request must be a JSON object")

        unknown = sorted(set(payload) - _ALLOWED_FIELDS)
        missing = sorted(_ALLOWED_FIELDS - set(payload))
        if unknown:
            raise ContractError(f"unsupported fields: {', '.join(unknown)}")
        if missing:
            raise ContractError(f"missing required fields: {', '.join(missing)}")

        current = EvidenceLevel.parse(payload["current_evidence_level"])
        verified = EvidenceLevel.parse(payload["verified_evidence_level"])
        requested = EvidenceLevel.parse(payload["requested_evidence_level"])
        if requested < current:
            raise ContractError("promotion requests may not lower the current evidence level")

        clinical_level = _require_nonempty_string(
            payload["clinical_safety_level"], "clinical_safety_level"
        ).upper()
        if clinical_level not in {"C0", "C1", "C2", "C3", "NOT_APPLICABLE"}:
            raise ContractError(f"unknown clinical safety level: {clinical_level!r}")

        return cls(
            artifact_id=_require_nonempty_string(payload["artifact_id"], "artifact_id"),
            current_evidence_level=current,
            verified_evidence_level=verified,
            requested_evidence_level=requested,
            requested_authority=AuthorityLevel.parse(payload["requested_authority"]),
            required_evidence=_string_tuple(payload["required_evidence"], "required_evidence"),
            verified_evidence=_string_tuple(payload["verified_evidence"], "verified_evidence"),
            recorded_evidence=_string_tuple(payload["recorded_evidence"], "recorded_evidence"),
            open_contradictions=_string_tuple(
                payload["open_contradictions"], "open_contradictions"
            ),
            recovery_dependencies_required=_string_tuple(
                payload["recovery_dependencies_required"],
                "recovery_dependencies_required",
            ),
            recovery_dependencies_present=_string_tuple(
                payload["recovery_dependencies_present"],
                "recovery_dependencies_present",
            ),
            self_issued_receipt_only=_strict_bool(
                payload["self_issued_receipt_only"], "self_issued_receipt_only"
            ),
            independent_reproduction_receipts=_nonnegative_int(
                payload["independent_reproduction_receipts"],
                "independent_reproduction_receipts",
            ),
            external_publication_claimed_as_evidence=_strict_bool(
                payload["external_publication_claimed_as_evidence"],
                "external_publication_claimed_as_evidence",
            ),
            external_publication_receipt_bound=_strict_bool(
                payload["external_publication_receipt_bound"],
                "external_publication_receipt_bound",
            ),
            governance_bundle_id=_optional_identifier(
                payload["governance_bundle_id"], "governance_bundle_id"
            ),
            gate_decision_id=_optional_identifier(
                payload["gate_decision_id"], "gate_decision_id"
            ),
            human_authority_id=_optional_identifier(
                payload["human_authority_id"], "human_authority_id"
            ),
            clinical_scope=_strict_bool(payload["clinical_scope"], "clinical_scope"),
            clinical_safety_level=clinical_level,
        )

    def to_primitive(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "current_evidence_level": self.current_evidence_level.name,
            "verified_evidence_level": self.verified_evidence_level.name,
            "requested_evidence_level": self.requested_evidence_level.name,
            "requested_authority": self.requested_authority.name,
            "required_evidence": list(self.required_evidence),
            "verified_evidence": list(self.verified_evidence),
            "recorded_evidence": list(self.recorded_evidence),
            "open_contradictions": list(self.open_contradictions),
            "recovery_dependencies_required": list(
                self.recovery_dependencies_required
            ),
            "recovery_dependencies_present": list(
                self.recovery_dependencies_present
            ),
            "self_issued_receipt_only": self.self_issued_receipt_only,
            "independent_reproduction_receipts": self.independent_reproduction_receipts,
            "external_publication_claimed_as_evidence": (
                self.external_publication_claimed_as_evidence
            ),
            "external_publication_receipt_bound": (
                self.external_publication_receipt_bound
            ),
            "governance_bundle_id": self.governance_bundle_id,
            "gate_decision_id": self.gate_decision_id,
            "human_authority_id": self.human_authority_id,
            "clinical_scope": self.clinical_scope,
            "clinical_safety_level": self.clinical_safety_level,
        }
