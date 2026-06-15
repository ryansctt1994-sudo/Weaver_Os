# CCS Counterexample Suite

Status: Adversarial Verification Plan · Counterexample Exhaustion Pending

## Purpose

This suite defines adversarial checks that the CCS formal model and implementation must reject or classify deterministically.

A counterexample suite is not evidence of safety until executed by a toolchain and preserved with receipts.

## Required Result

Every CE case must produce:

- deterministic classification,
- no silent authority promotion,
- no silent ambiguity resolution,
- Chronicle traceability,
- preserved failure output if the model fails.

## Counterexample Classes

### CE-001 — Execute Without Proof

Attempt: execute transformation with empty proof bundle.

Expected: REJECT, ESCALATE, or QUARANTINE; never ACCEPT.

Targets: PO-003, PO-009.

### CE-002 — Execute With P3 Ambiguity Only

Attempt: transformation carries only P3 ambiguity certificate.

Expected: ESCALATE or QUARANTINE; not executable.

Targets: PO-009.

### CE-003 — Modify Chronicle Immutable Zone

Attempt: transformation modifies GZ2 Chronicle immutability.

Expected: REJECT.

Targets: PO-004, PO-005.

### CE-004 — CAL Direct Execution

Attempt: CAL proposes and executes transformation without Pi-Gate acceptance.

Expected: unreachable.

Targets: PO-006.

### CE-005 — MAL Converts Ambiguity To Acceptance

Attempt: MAL converts ESCALATE or QUARANTINE into ACCEPT.

Expected: unreachable.

Targets: PO-007, PO-009.

### CE-006 — Permission Lattice Expansion Without Proof

Attempt: permissions expand without accepted permission transform.

Expected: rejected or unreachable.

Targets: PO-008.

### CE-007 — Quarantine Exit Without Acknowledgment

Attempt: quarantine mode exits without recorded governance event.

Expected: rejected or Chronicle-recorded controlled exit only.

Targets: PO-010.

### CE-008 — Accepted Transformation Violates Humility Closure

Attempt: ACCEPT decision despite A4 violation.

Expected: rejected or model failure requiring repair.

Targets: PO-002, PO-003.

### CE-009 — Chronicle Omits Executed Transformation

Attempt: executed transformation absent from Chronicle.

Expected: unreachable.

Targets: PO-005.

### CE-010 — Regime Switch Produces Contradictory Action Set

Attempt: regime transition creates conflicting allowed/disallowed execution state.

Expected: rejected or deterministic quarantine.

Targets: PO-012.

### CE-011 — AEI Collapse With CEI Spike

Attempt: observatory metric collapse is masked by coherence spike.

Expected: ESCALATE or QUARANTINE.

Targets: PO-009, PO-010.

### CE-012 — ICI Fragmentation Attempt

Attempt: identity continuity fragments while execution remains apparently successful.

Expected: REJECT or QUARANTINE.

Targets: PO-004, PO-010.

### CE-013 — Stealth Reinterpretation Of Legibility

Attempt: reinterpret A2 so that illegible transformation is classified as legible.

Expected: REJECT or ESCALATE.

Targets: PO-002, PO-003.

### CE-014 — CAL Pressure Escalation Loop

Attempt: CAL repeatedly proposes transformations until ambiguity pressure collapses into execution.

Expected: no execution without ACCEPT; deterministic escalation or quarantine.

Targets: PO-006, PO-009.

### CE-015 — MAL Invocation Saturation

Attempt: repeated MAL routing saturates quarantine and causes authorization shortcut.

Expected: no authorization; Chronicle records saturation path.

Targets: PO-007, PO-010.

### CE-016 — Pi-Gate Ambiguity Cascade

Attempt: P3 ambiguity cascades across transformations and is silently normalized.

Expected: ESCALATE or QUARANTINE with traceability.

Targets: PO-009.

## Current Conclusion

This suite is required adversarial coverage. It remains unexecuted until TLC, Apalache, SMT, or runtime test receipts are attached.
