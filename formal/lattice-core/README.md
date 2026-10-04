# Weaver Lattice Core v0.1

Standalone read-only Lean library pinned to `leanprover/lean4:v4.22.0`, with no
external Lake packages. It does not certify the unseen `introspection-twin`
source tree or grant runtime permission or authority.

`LatticeCore/Deflation.lean` defines explicit order/meet laws and separate
propositions for deflationarity, inflationarity, monotonicity and idempotence.
Fixed-ceiling meet restriction has separately proved deflationarity,
monotonicity and idempotence. Composition preserves deflationarity and
monotonicity; idempotence of composition additionally requires commutation.

`Models.lean` distinguishes permission predicates ordered by inclusion,
assurance rungs with minimum as meet, and information accumulation by union.
These are mathematical models, not verified integrations with Crosswalk,
nms-engine, axis_guard or the epistemic diode.

`Counterexamples.lean` proves that deflationarity does not imply monotonicity
and that deflationarity plus monotonicity does not imply idempotence.
`Audit.lean` reports transitive dependencies for all 16 theorems. Standard
Lean axioms `propext` and `Quot.sound` are exposed; `sorryAx` is forbidden.

Reproduce from this directory:

```
lake build
lake env lean -DwarningAsError=true Audit.lean
```

CI uses a digest-pinned Lean release, retains source SHA, tool identity, build
and axiom logs and hashes, and rejects build warnings or `sorryAx`. The kernel
checks these sources; this adds no evidence for earlier unseen build claims.

Local verification environment note: this session's container exposed
`/proc/self/exe` but not Lean's numeric `/proc/<pid>/exe` lookup. Local compilation
used a narrow `readlink` compatibility interposer for that path only, with the
unmodified 4.22.0 release binaries. CI performs the clean build without that
interposer. Local source-hashed reports marked `dirty: true` are development
evidence; the clean CI report is the source-commit qualification gate.
