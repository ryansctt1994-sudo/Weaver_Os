"""Evidence promotion helpers for Cathedral MVP-0."""

from __future__ import annotations

from .evidence_registry import EvidenceRecord, EvidenceRegistry, EvidenceRegistryError
from .qgs import QGSLevel


REQUIRED_PROMOTION_BASIS: dict[QGSLevel, tuple[str, ...]] = {
    QGSLevel.E1_SPEC: ("spec", "design"),
    QGSLevel.E2_IMPLEMENTED: ("source", "code", "implementation"),
    QGSLevel.E3_RECEIPTED: ("receipt", "pytest", "test", "hash", "ci"),
    QGSLevel.E4_REPLICATED: ("replicated", "independent", "replay"),
    QGSLevel.E5_AUDITED: ("audit", "audited", "production", "deployment", "monitoring"),
}


def promote_with_basis_check(
    registry: EvidenceRegistry,
    artifact_id: str,
    new_level: QGSLevel,
    basis: str,
) -> EvidenceRecord:
    """Promote evidence only when the basis contains level-appropriate language.

    This is an MVP-0 guardrail.  It does not prove the basis is true.  It blocks
    obviously unsupported promotions such as promoting to E3 without mentioning
    any receipt, test, hash, CI, or replay evidence.
    """

    basis_lower = basis.lower()
    required_terms = REQUIRED_PROMOTION_BASIS.get(new_level, ())
    if required_terms and not any(term in basis_lower for term in required_terms):
        raise EvidenceRegistryError(
            f"basis for {new_level.name} must reference one of: {', '.join(required_terms)}"
        )
    return registry.promote(artifact_id, new_level, basis)
