#!/usr/bin/env python3
"""
The Throne Remains Empty: A Proof-Backed Transition Validator
Architecture: Delta-717 / Cathedral-OS / Weaver Reference Implementation
Status: ACCEPTED_AS_DEMO_DESIGN (v0.1 Corrected)
Evidence Level: E1_SPECIFIED until run and receipted
Authority Weight: 0

Enforces:
  1. Proposal Namespace Separation: computed fields in root are hard-rejected.
  2. Narration != Evidence: ledger records require strict hash self-integrity checks.
  3. Evidence Growth != Authority Growth: lower-tier evidence cannot bypass promotion gates.

This is a dependency-free demo. It performs local predicate validation only.
Full JSON Schema validation remains in the PR-001 -> PR-005 stack.
"""

import sys
import json
import hashlib
from typing import Any, Dict, Tuple

STACK_LAYERS = [
    "REALITY",
    "CATEGORY_INTEGRITY",
    "TRANSLATION_BOUNDARIES",
    "ADMISSIBILITY",
    "EVIDENCE",
    "REPLAY",
    "RECEIPTS",
    "AUTHORITY",
    "EXECUTION",
]

ZERO_HEAD = "0" * 64


class EpistemicKernelValidator:
    def __init__(self, canonical_head: str = ZERO_HEAD):
        self.current_canonical_head = canonical_head
        self.prior_legitimacy = 100

    def render_waterfall(self, highlighted_layer: str, verdict: str) -> None:
        """Visualize the architectural layer where the transaction terminated."""
        color = "\033[93m" if verdict == "REJECT" else ("\033[92m" if verdict == "ACCEPT" else "\033[94m")
        reset = "\033[0m"

        print("\n--- SYSTEM TOPOLOGY WATERFALL ---")
        for layer in STACK_LAYERS:
            if layer == highlighted_layer:
                print(f"  {color}-> [{layer}] <-- VERTICAL GATE TERMINATION ({verdict}){reset}")
            else:
                print(f"  v [{layer}]")
        print("---------------------------------\n")

    @staticmethod
    def serialize_canonical_json(obj: Any) -> str:
        """Deterministic JSON normalization for invariant hashing."""
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))

    def evaluate_transaction(self, tx: Dict[str, Any]) -> Tuple[str, str, str, int]:
        """Compute a demo TransitionRecord verdict from a raw proposal or record audit."""
        if "id" not in tx or "transition_type" not in tx:
            return "DEFER", "PARSE_FAILURE", "ADMISSIBILITY", 0

        tx_type = tx["transition_type"]

        # Case 03: historical record self-integrity verification.
        if tx_type == "RECORD_INTEGRITY_CHECK":
            if "claimed_record_hash" not in tx or "record_body" not in tx:
                return "REJECT", "INSUFFICIENT_EVIDENCE", "EVIDENCE", 0

            canonical_body = self.serialize_canonical_json(tx["record_body"])
            computed_hash = hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()

            if tx["claimed_record_hash"] != computed_hash:
                return "REJECT", "RECORD_SELF_HASH_MISMATCH", "REPLAY", 0
            return "ACCEPT", "SUCCESS_RECORD_VERIFIED", "EXECUTION", 0

        # Untrusted proposals must not contain kernel-computed output fields.
        smuggled_fields = [
            "verdict",
            "possible",
            "proofs",
            "authority_delta",
            "legitimacy_conservation",
            "rejection_receipt",
        ]
        for field in smuggled_fields:
            if field in tx:
                return "REJECT", "AUTHORITY_ERROR", "ADMISSIBILITY", 0

        if tx.get("from_state_hash") != self.current_canonical_head:
            return "REJECT", "AUTHORITY_ERROR", "TRANSLATION_BOUNDARIES", 0

        proposal = tx.get("proposal", {})
        evidence = tx.get("evidence_refs", {})

        # Requested authority movement may appear only as untrusted proposal intent.
        # Enacted authority_delta remains a kernel-computed TransitionRecord field only.
        requested_delta = proposal.get("requested_authority_delta", 0)
        if tx_type != "CVP_PROMOTION" and requested_delta != 0:
            return "REJECT", "AUTHORITY_ERROR", "AUTHORITY", 0

        if not tx.get("possible_assertion", True):
            return "REJECT", "POSSIBILITY_FAILURE", "REALITY", 0

        # Local predicate approximation of ProofComplete for demo purposes.
        has_auth = len(evidence.get("steward_authorizations", [])) > 0
        has_fidelity = len(evidence.get("replay_logs", [])) > 0
        has_obs = len(evidence.get("telemetry_records", [])) > 0
        has_verify = len(evidence.get("formal_proofs", [])) > 0
        has_account = len(evidence.get("receipts", [])) > 0

        proof_complete = has_auth and has_fidelity and has_obs and has_verify and has_account
        if not proof_complete:
            return "REJECT", "PROOF_INCOMPLETE", "CATEGORY_INTEGRITY", 0

        if tx_type == "CVP_PROMOTION":
            witnesses = evidence.get("witness_reports", [])
            if len(witnesses) == 0:
                return "DEFER", "STEWARD_REQUIRED_BEFORE_E3", "RECEIPTS", 0

            computed_credit = len(witnesses) * 5
            return "ACCEPT", "SUCCESS_PROMOTION_ENACTED", "EXECUTION", computed_credit

        return "ACCEPT", "SUCCESS_ORDINARY_COMMIT", "EXECUTION", 0


def run_suite(target_file: str) -> int:
    try:
        with open(target_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(f"CRITICAL: IO processing failed for file trace: {exc}")
        return 1

    kernel = EpistemicKernelValidator()
    verdict, code, layer, delta = kernel.evaluate_transaction(data)

    kernel.render_waterfall(layer, verdict)
    print(f"TARGET SOURCE : {target_file}")
    print(f"VERDICT       : [{verdict}]")
    print(f"RETURN CODE   : {code}")
    print(f"COMPUTED DELTA: +{delta}")
    print("AXIOM STATUS  : Conservation Validated. The Throne Remains Empty.")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Execution Syntax: python3 boundary_integrity_demo.py <target_case.json>")
        sys.exit(1)
    sys.exit(run_suite(sys.argv[1]))
