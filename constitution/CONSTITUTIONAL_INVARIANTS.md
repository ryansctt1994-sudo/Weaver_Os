# Constitutional Invariants

The following invariants are non-authority-preserving constraints for the Weaver Governance Runtime.

## Core Invariants

- Capability ≠ Authority
- Evidence ≠ Truth
- Replay ≠ Promotion
- Promotion ≠ Operational Authority
- Documentation ≠ Implementation
- Consensus ≠ Verification
- Consensus ≠ Correctness
- Coherence ≠ Truth
- Memory ≠ Governance
- Governance ≠ Control
- Containment ≠ Grounding
- Test Success ≠ Production Readiness

## Authority Discipline

Authority must be explicit, scoped, recorded, revocable, replayable, and accountable.

No mechanism may silently convert uncertainty, unfamiliarity, consensus, continuity, or capability into authority.

## VEC-SLICE-01 — Edge-Weights Type Decision

For Weaver OS v1.0 RC, the `WeaverPolicy` trait may use `&mut Vec<f32>` for edge weights. Zero-copy slices (`&mut [f32]`) may be introduced in v1.1 only after performance profiling demonstrates a measurable bottleneck. The current choice is acceptable when documented and tested.
