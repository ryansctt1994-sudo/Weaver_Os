# WNS Formal Kernel v0.1

Small Lean 4.19.0 model shared by constructed Weaver and Commons scenarios.
No mathlib or external Lean packages are required.

```sh
lake build
lake env lean Audit.lean
```

Core covers grant membership, explicit trusted issuer roots, subject/action scope,
time windows, revocation, current evidence, protected-state transitions, receipts,
append-preserved history, authority reset at seams, and deterministic proposal
replay. Rejection preserves protected state while adding an audit receipt.

The initial grant store and trusted roots are supplied assumptions. The model does
not authenticate grant minting or prove the human legitimacy of those roots.
Scope attenuation proves scope containment only, not full delegation validity.
Receipt fields bind abstract values; they do not implement cryptographic signing.
Replay assumes fixed roots, grants, time and deterministic transition semantics;
it does not authenticate a real history or prove its completeness.

Instances use a counter and a separate Commons routing relation. They are concrete
examples of the abstract model, not correspondence proofs for existing Python
programs. No health efficacy, Academy learning, consciousness, or independent
reproduction claim follows. Academy model runs remain on hold.

False-Green countermodels establish failed implications within declared models.
The commitment example is modulo two, not an exhibited SHA-256 collision. The
report and emergency examples show independently represented attributes, not
empirical findings or a proof that an emergency policy is morally correct.

Build status must come from successful pinned compilation and axiom audit logs.
No `sorry`, custom axiom, or `native_decide` is used. Standard Lean logical axioms
may appear in the audit. Passing author-controlled CI remains project-side evidence.
Runtime refinement and independent reproduction are separate work.

## Temporal extension

Execution runs preserve existing receipt membership and stored grants. Exact grant
removal denies that grant through subsequent modeled executions. Minting, concurrent
revocation propagation, equivalent replacement grants, and runtime races are outside
this result. Copy/seam resets create a new history context; the preservation theorem
does not cover seams or arbitrary administrative edits.

Bounded delegation constrains scope, time window, budget, remaining depth, and issuer
linkage. The lineage predicate requires a trusted origin. These are admission
conditions, not proof of signed minting, live ancestor revocation, or budget spending.

NEXUS-style invalidation covers recorded direct dependencies; unrecorded or transitive
dependencies need an explicit expansion policy. A changed recorded source sets currency
false and prevents the corresponding protected transition.

Receipt replay checks before-state continuity and verdict-dependent after-state
consistency. Valid modeled chains reconstruct their final state, and each kernel
step emits a consistent replayable receipt. This does not authenticate receipts,
prove eligibility from receipt fields, or establish history completeness. The receipts
lack grants/evidence, so receipt replay is a consistency check, not authorization.
