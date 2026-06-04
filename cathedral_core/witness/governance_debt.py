"""Governance debt primitives.

Governance debt captures unresolved verification, replay, attestation, authority,
scope, signal, outcome, and egress obligations.  Debt is fail-closed by default:
it starts unresolved and requires a complete proof bundle to close.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .receipt import ProofBundle


class DebtType(str, Enum):
    VERIFICATION_DEBT = "VERIFICATION_DEBT"
    REPLAY_DEBT = "REPLAY_DEBT"
    ATTESTATION_DEBT = "ATTESTATION_DEBT"
    AUTHORITY_DEBT = "AUTHORITY_DEBT"
    SCOPE_DEBT = "SCOPE_DEBT"
    SIGNAL_DEBT = "SIGNAL_DEBT"
    OUTCOME_DEBT = "OUTCOME_DEBT"
    EGRESS_DEBT = "EGRESS_DEBT"

    # Backward-compatible alias used in earlier MVP-0 drafts.
    WITNESS_DEBT = "ATTESTATION_DEBT"


@dataclass
class GovernanceDebt:
    """Open governance obligation requiring receipt-backed resolution."""

    debt_type: DebtType
    description: str
    receipt_required: bool = True
    resolved: bool = False
    proof_bundle: Optional[ProofBundle] = None

    def resolve(self, proof_bundle: ProofBundle) -> None:
        """Resolve the debt only with a complete proof bundle."""

        if self.receipt_required and not proof_bundle.is_complete():
            raise ValueError("Governance debt requires complete proof receipts")
        self.proof_bundle = proof_bundle
        self.resolved = True
