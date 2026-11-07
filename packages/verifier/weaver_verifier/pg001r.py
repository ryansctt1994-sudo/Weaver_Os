"""PG-001R clean-room, read-only promotion-gate verifier.

The gate evaluates a fully formed promotion request against the frozen PG-001R
specification. It does not mutate state, sign receipts, close contradictions,
or grant authority outside the returned deterministic decision object.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from weaver_contracts.pg001r import (
    AUTHORITY_EVIDENCE_FLOOR,
    AuthorityLevel,
    PromotionRequest,
)


@dataclass(frozen=True, order=True)
class Blocker:
    code: str
    rule: str
    detail: str

    def to_primitive(self) -> dict[str, str]:
        return {"code": self.code, "rule": self.rule, "detail": self.detail}


@dataclass(frozen=True)
class PromotionDecision:
    artifact_id: str
    allowed: bool
    requested_evidence_level: str
    requested_authority: str
    effective_evidence_level: str
    eligible_authority: str
    blockers: tuple[Blocker, ...]
    request_fingerprint_sha256: str
    decision_fingerprint_sha256: str
    implementation_evidence_ceiling: str = "R2[self]"
    implementation_authority: str = "NONE"

    def to_primitive(self, *, include_decision_fingerprint: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "artifact_id": self.artifact_id,
            "allowed": self.allowed,
            "requested_evidence_level": self.requested_evidence_level,
            "requested_authority": self.requested_authority,
            "effective_evidence_level": self.effective_evidence_level,
            "eligible_authority": self.eligible_authority,
            "blockers": [blocker.to_primitive() for blocker in self.blockers],
            "request_fingerprint_sha256": self.request_fingerprint_sha256,
            "implementation_evidence_ceiling": self.implementation_evidence_ceiling,
            "implementation_authority": self.implementation_authority,
        }
        if include_decision_fingerprint:
            payload["decision_fingerprint_sha256"] = self.decision_fingerprint_sha256
        return payload


def _canonical_bytes(payload: object) -> bytes:
    """Return deterministic JSON bytes for non-authoritative fingerprints.

    This is PG001R-JSON-1, not triweavon-cjson-v1 and not a receipt format.
    """

    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _missing(required: Iterable[str], present: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(required) - set(present)))


def evaluate(request: PromotionRequest) -> PromotionDecision:
    blockers: list[Blocker] = []

    if request.requested_evidence_level > request.verified_evidence_level:
        blockers.append(
            Blocker(
                "B01",
                "EVIDENCE_CEILING",
                (
                    f"requested {request.requested_evidence_level.name} exceeds "
                    f"verified {request.verified_evidence_level.name}"
                ),
            )
        )

    missing_required_evidence = _missing(
        request.required_evidence, request.verified_evidence
    )
    if missing_required_evidence:
        blockers.append(
            Blocker(
                "I01",
                "REQUIRED_EVIDENCE_SUBSET",
                "required evidence is not verified: "
                + ", ".join(missing_required_evidence),
            )
        )

    unrecorded_verified_evidence = _missing(
        request.verified_evidence, request.recorded_evidence
    )
    if unrecorded_verified_evidence:
        blockers.append(
            Blocker(
                "I02",
                "VERIFIED_EVIDENCE_SUBSET",
                "verified evidence is not recorded: "
                + ", ".join(unrecorded_verified_evidence),
            )
        )

    if request.requested_evidence_level.value >= 4:
        reasons: list[str] = []
        if request.self_issued_receipt_only:
            reasons.append("receipt set is self-issued only")
        if request.independent_reproduction_receipts < 2:
            reasons.append("fewer than two independent reproduction receipts")
        if reasons:
            blockers.append(
                Blocker(
                    "B02",
                    "ILLEGAL_SELF_PROMOTION",
                    "; ".join(reasons),
                )
            )

    if request.open_contradictions:
        blockers.append(
            Blocker(
                "B03",
                "OPEN_CONTRADICTIONS",
                "open contradiction IDs: " + ", ".join(sorted(request.open_contradictions)),
            )
        )

    missing_recovery = _missing(
        request.recovery_dependencies_required,
        request.recovery_dependencies_present,
    )
    if missing_recovery:
        blockers.append(
            Blocker(
                "B04",
                "MISSING_RECOVERY_DEPENDENCIES",
                "missing recovery dependencies: " + ", ".join(missing_recovery),
            )
        )

    if (
        request.external_publication_claimed_as_evidence
        and request.requested_evidence_level > request.current_evidence_level
        and not request.external_publication_receipt_bound
    ):
        blockers.append(
            Blocker(
                "B05",
                "EXTERNAL_PUBLICATION_INFLATION",
                "external publication is used for promotion without an artifact-bound receipt",
            )
        )

    if request.requested_authority > AuthorityLevel.NONE:
        missing_governance: list[str] = []
        if request.governance_bundle_id is None:
            missing_governance.append("governance_bundle_id")
        if request.gate_decision_id is None:
            missing_governance.append("gate_decision_id")
        if request.human_authority_id is None:
            missing_governance.append("human_authority_id")

        floor = AUTHORITY_EVIDENCE_FLOOR[request.requested_authority]
        if request.requested_evidence_level < floor:
            missing_governance.append(
                f"evidence floor {floor.name} for {request.requested_authority.name}"
            )

        if missing_governance:
            blockers.append(
                Blocker(
                    "B06",
                    "AUTHORITY_WITHOUT_GOVERNANCE",
                    "missing or unsatisfied authority controls: "
                    + ", ".join(missing_governance),
                )
            )

    if request.clinical_scope and request.clinical_safety_level == "C0":
        if (
            request.requested_evidence_level > request.current_evidence_level
            or request.requested_authority > AuthorityLevel.NONE
        ):
            blockers.append(
                Blocker(
                    "B07",
                    "CLINICAL_C0_BLOCK",
                    "clinical C0 artifacts may not be promoted or granted authority",
                )
            )

    ordered = tuple(sorted(blockers))
    allowed = not ordered
    request_fingerprint = _fingerprint(request.to_primitive())

    partial = PromotionDecision(
        artifact_id=request.artifact_id,
        allowed=allowed,
        requested_evidence_level=request.requested_evidence_level.name,
        requested_authority=request.requested_authority.name,
        effective_evidence_level=(
            request.requested_evidence_level.name
            if allowed
            else request.current_evidence_level.name
        ),
        eligible_authority=(
            request.requested_authority.name if allowed else AuthorityLevel.NONE.name
        ),
        blockers=ordered,
        request_fingerprint_sha256=request_fingerprint,
        decision_fingerprint_sha256="",
    )
    decision_fingerprint = _fingerprint(
        partial.to_primitive(include_decision_fingerprint=False)
    )
    return PromotionDecision(
        artifact_id=partial.artifact_id,
        allowed=partial.allowed,
        requested_evidence_level=partial.requested_evidence_level,
        requested_authority=partial.requested_authority,
        effective_evidence_level=partial.effective_evidence_level,
        eligible_authority=partial.eligible_authority,
        blockers=partial.blockers,
        request_fingerprint_sha256=partial.request_fingerprint_sha256,
        decision_fingerprint_sha256=decision_fingerprint,
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python -m weaver_verifier.pg001r REQUEST.json",
            file=sys.stderr,
        )
        return 2

    path = Path(args[0])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = PromotionRequest.from_mapping(payload)
        decision = evaluate(request)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PG-001R input rejected: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(decision.to_primitive(), indent=2, sort_keys=True))
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
