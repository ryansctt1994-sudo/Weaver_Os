from cathedral_core.witness.qgs import QGSLevel
from cathedral_core.witness.receipt import ProofBundle


def test_complete_proof_bundle_is_complete():
    bundle = ProofBundle(
        proposal_receipt="proposal:001",
        admissibility_receipt="admissibility:001",
        witness_receipt="witness:001",
        execution_receipt="execution:001",
    )

    assert bundle.is_complete()
    assert bundle.evidence_level == QGSLevel.E3_RECEIPTED


def test_incomplete_proof_bundle_is_not_complete():
    bundle = ProofBundle(
        proposal_receipt="proposal:001",
        admissibility_receipt="",
        witness_receipt="witness:001",
        execution_receipt="execution:001",
    )

    assert not bundle.is_complete()
