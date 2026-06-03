import pytest

from cathedral_core.witness.evidence_promotion import promote_with_basis_check
from cathedral_core.witness.evidence_registry import EvidenceRegistry, EvidenceRegistryError
from cathedral_core.witness.qgs import QGSLevel


def test_evidence_registry_registers_artifact():
    registry = EvidenceRegistry()

    record = registry.register("authority_fsm.py", QGSLevel.E2_IMPLEMENTED, "source code exists")

    assert record.artifact_id == "authority_fsm.py"
    assert record.level == QGSLevel.E2_IMPLEMENTED
    assert record.basis == "source code exists"
    assert record.history == []


def test_evidence_registry_rejects_empty_artifact_or_basis():
    registry = EvidenceRegistry()

    with pytest.raises(EvidenceRegistryError):
        registry.register("", QGSLevel.E0_CLAIM, "claim recorded")

    with pytest.raises(EvidenceRegistryError):
        registry.register("artifact", QGSLevel.E0_CLAIM, "")


def test_evidence_registry_rejects_duplicate_registration():
    registry = EvidenceRegistry()
    registry.register("artifact", QGSLevel.E1_SPEC, "spec exists")

    with pytest.raises(EvidenceRegistryError):
        registry.register("artifact", QGSLevel.E1_SPEC, "spec exists again")


def test_evidence_registry_promotes_monotonically_and_records_history():
    registry = EvidenceRegistry()
    registry.register("qgs.py", QGSLevel.E1_SPEC, "spec exists")

    record = registry.promote("qgs.py", QGSLevel.E2_IMPLEMENTED, "source code exists")

    assert record.level == QGSLevel.E2_IMPLEMENTED
    assert record.basis == "source code exists"
    assert len(record.history) == 1
    assert record.history[0].previous_level == QGSLevel.E1_SPEC
    assert record.history[0].new_level == QGSLevel.E2_IMPLEMENTED


def test_evidence_registry_rejects_equal_level_or_downgrade_as_promotion():
    registry = EvidenceRegistry()
    registry.register("artifact", QGSLevel.E2_IMPLEMENTED, "source code exists")

    with pytest.raises(EvidenceRegistryError):
        registry.promote("artifact", QGSLevel.E2_IMPLEMENTED, "same level restatement")

    with pytest.raises(EvidenceRegistryError):
        registry.promote("artifact", QGSLevel.E1_SPEC, "downgrade attempted")


def test_promote_with_basis_check_rejects_e3_without_receipt_language():
    registry = EvidenceRegistry()
    registry.register("authority_fsm.py", QGSLevel.E2_IMPLEMENTED, "source code exists")

    with pytest.raises(EvidenceRegistryError):
        promote_with_basis_check(
            registry,
            "authority_fsm.py",
            QGSLevel.E3_RECEIPTED,
            "looks mature",
        )


def test_promote_with_basis_check_accepts_e3_receipt_language():
    registry = EvidenceRegistry()
    registry.register("authority_fsm.py", QGSLevel.E2_IMPLEMENTED, "source code exists")

    record = promote_with_basis_check(
        registry,
        "authority_fsm.py",
        QGSLevel.E3_RECEIPTED,
        "pytest receipt and sha256 hash captured",
    )

    assert record.level == QGSLevel.E3_RECEIPTED
