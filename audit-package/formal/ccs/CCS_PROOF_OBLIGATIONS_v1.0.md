# CCS Proof Obligations v1.0

Status: Proof Inventory · Verification Pending · Authority Neutral

## Purpose

This ledger converts the CCS formal verification schema into explicit proof obligations.

It separates formal specification from verified evidence. A proof obligation is not a proof. A modeled property is not an externally validated property. Authority remains unearned until evidence passes the required ladder.

## Status Labels

- UNMODELED: predicate or theorem not yet formalized.
- MODELED: formal statement exists.
- MODEL_CHECKED: checked by TLC, Apalache, or equivalent bounded tool.
- SMT_VALIDATED: discharged by SMT solver.
- INTERDEPENDENTLY_REPRODUCED: reproduced by a non-originating reviewer or environment.
- EXTERNALLY_AUDITED: reviewed by external auditor.
- FAILED: counterexample found.

## Obligations

### PO-001 — Type Safety

Source: TypeOK.

Theorem: all reachable states satisfy declared type constraints.

Verification route: TLA+, TLC, Apalache.

Current status: MODELED.

Evidence: pending.

### PO-002 — Genesis Preservation

Source: GenesisPreserved(T,S).

Theorem: accepted transformations preserve all Genesis axioms.

Verification route: SMT and interactive proof after preservation predicates are concretized.

Current status: UNMODELED / PARTIAL.

Evidence: pending.

### PO-003 — Pi-Gate Soundness

Source: PiDecision / admissibility function.

Theorem: Pi-Gate ACCEPT implies GenesisPreserved, HasValidProof, and no immutable-zone violation.

Verification route: TLA+, SMT.

Current status: MODELED.

Evidence: pending.

### PO-004 — Immutable Zone Protection

Source: GZ1 through GZ4.

Theorem: immutable zones are never modified by executable transformations.

Verification route: TLA+, SMT.

Current status: MODELED.

Evidence: pending.

### PO-005 — Chronicle Append-Only

Source: ChroniclePrefixInvariant.

Theorem: Chronicle may append but may not reorder, rewrite, or delete prior entries.

Verification route: TLA+, TLC, Apalache.

Current status: MODELED.

Evidence: pending.

### PO-006 — CAL Non-Execution

Source: CALCannotExecute.

Theorem: CAL may propose transformations but may not execute them.

Verification route: TLA+, TLC.

Current status: MODELED.

Evidence: pending.

### PO-007 — MAL Non-Authorization

Source: MALCannotAuthorize.

Theorem: MAL may route ambiguity or quarantine states but may not authorize execution.

Verification route: TLA+, TLC.

Current status: MODELED.

Evidence: pending.

### PO-008 — Permission Non-Expansion

Source: PermissionNonExpansion / CSBS.

Theorem: permission lattice cannot expand without accepted proof and admissible governance.

Verification route: TLA+, Apalache, SMT.

Current status: MODELED / PARTIAL.

Evidence: pending.

### PO-009 — Ambiguity Preservation

Source: NoAmbiguityCollapse.

Theorem: ESCALATE or QUARANTINE decisions cannot silently execute.

Verification route: TLA+, SMT.

Current status: MODELED.

Evidence: pending.

### PO-010 — Quarantine Safety

Source: QuarantineSafety.

Theorem: quarantine mode preserves origin trace and interpretive legibility.

Verification route: TLA+, SMT after semantic predicates are concretized.

Current status: UNMODELED / PARTIAL.

Evidence: pending.

### PO-011 — Liveness Under Admissible Progress

Source: AcceptedEventuallyExecuted, RejectedEventuallyCleared, AmbiguityEventuallyHandled.

Theorem: accepted, rejected, and ambiguous transformations eventually resolve under fairness assumptions.

Verification route: TLA+ liveness checking.

Current status: MODELED / FAIRNESS_PENDING.

Evidence: pending.

### PO-012 — Regime Transition Consistency

Source: CAL regimes and transition semantics.

Theorem: regime transitions do not produce contradictory action sets or hidden authority expansion.

Verification route: TLA+, Apalache.

Current status: UNMODELED / PARTIAL.

Evidence: pending.

## Evidence Rule

No obligation may be promoted from MODELED to MODEL_CHECKED, SMT_VALIDATED, INTERDEPENDENTLY_REPRODUCED, or EXTERNALLY_AUDITED without attached receipts.

## Current Conclusion

The proof inventory is mature enough to guide verification work, but no Tier-3 verification authority is claimed by this document.
