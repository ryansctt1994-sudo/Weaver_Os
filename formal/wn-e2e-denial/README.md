# Weaver denial-preservation extension v0.1 — CHECK PENDING

Prepared September 25, 2026 (America/Chicago).

This package contains seven proposed Lean proofs extending the unchanged
Weaver Formal Core v0.1. The source is written, but compilation of this extension
has NOT been established. The downloaded Lean 4.19.0 executable failed before
elaboration with `error: failed to locate application` in the current environment.
Do not count these additions as kernel-checked proofs yet.

## Claims encoded

1. A false authorization check leaves the entire modeled state unchanged.
2. A grant absent from the state's grant list leaves state unchanged.
3. A revoked grant leaves state unchanged.
4. An expired grant leaves state unchanged.
5. Any denied execution event leaves state unchanged.
6. Any finite trace consisting of denied execution events leaves state unchanged.
7. Any pure observation of state is preserved by a denied execution.

The trace claim covers failed policy checks, not every possible reason for denial.
The state includes grants, receipts and executed bindings. No rejection logging
is modeled here. The Python demo appends rejection audit records outside its
protected state, so a refinement must specify which fields correspond.

`Core.lean` is byte-for-byte copied from
WEAVER_FORMAL_CORE_v0.1_2026-09-22.zip, member WEAVER_FORMAL_CORE_v0.1/Core.lean.
`Denial.lean` is the new extension. No modifications to the base core are required.

## Recheck

The draft PR runs `.github/workflows/wn-e2e-denial.yml` with the official Lean 4.19.0 toolchain. Locally, install Lean 4.19.0, put `lean` on PATH, then run:

```
python3 verify.py
```

The verifier recompiles Core.lean before Denial.lean, fails on compiler errors,
rejects placeholder proofs, and records the output and exit codes. Existing
build logs are diagnostics from this environment, not successful verification.

## Limits

Even successful compilation proves only the definitions in this abstract model.
It does not prove Python correspondence, authentic grant issuance, trusted time,
cryptographic security, a real-world execution boundary, or production safety.
State equality implies equal outputs from a pure hash function; hash equality
alone does not imply state equality. No hash injectivity assumption is added.
The seven declarations contain no sorry/admit or new axioms; compiler checking
and printed axiom inspection remain required. W0/O0 unchanged.
