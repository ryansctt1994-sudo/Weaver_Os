import pytest

from cathedral_core.witness.governance_debt import DebtType, GovernanceDebt
from cathedral_core.witness.receipt import ProofBundle


def complete_bundle() -> ProofBundle:
    return ProofBundle(
        proposal_receipt="proposal:001",
        admissibility_receipt="admissibility:001",
        witness_receipt="witness:001",
        execution_receipt="execution:001",
    )


def incomplete_bundle() -> ProofBundle:
    return ProofBundle(
        proposal_receipt="proposal:001",
        admissibility_receipt="",
        witness_receipt="witness:001",
        execution_receipt="execution:001",
    )


def test_governance_debt_is_unresolved_by_default():
    debt = GovernanceDebt(DebtType.REPLAY_DEBT, "MANIFEST.sha256 not found")

    assert debt.debt_type == DebtType.REPLAY_DEBT
    assert debt.resolved is False
    assert debt.receipt_required is True
    assert debt.proof_bundle is None


def test_governance_debt_rejects_incomplete_receipt_when_required():
    debt = GovernanceDebt(DebtType.VERIFICATION_DEBT, "source bytes missing")

    with pytest.raises(ValueError):
        debt.resolve(incomplete_bundle())

    assert debt.resolved is False
    assert debt.proof_bundle is None


def test_governance_debt_resolves_with_complete_receipt():
    debt = GovernanceDebt(DebtType.WITNESS_DEBT, "witness receipt pending")
    bundle = complete_bundle()

    debt.resolve(bundle)

    assert debt.resolved is True
    assert debt.proof_bundle == bundle
