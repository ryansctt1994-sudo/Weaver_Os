"""Proof bundle data contract for MVP-0.

A proof bundle does not execute anything.  It records the minimum receipt spine
needed to close a governance-debt item: proposal, admissibility, witness, and
execution receipts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .qgs import QGSLevel


@dataclass(frozen=True)
class ProofBundle:
    """Receipt bundle required to resolve governance debt."""

    proposal_receipt: str
    admissibility_receipt: str
    witness_receipt: str
    execution_receipt: str
    evidence_level: QGSLevel = QGSLevel.E3_RECEIPTED

    def is_complete(self) -> bool:
        """Return True only when all receipt fields are non-empty."""

        return all(
            bool(value)
            for value in (
                self.proposal_receipt,
                self.admissibility_receipt,
                self.witness_receipt,
                self.execution_receipt,
            )
        )
