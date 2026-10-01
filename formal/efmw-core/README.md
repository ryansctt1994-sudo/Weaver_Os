# EFMW Residual Core v0.1

Attribution: EFMW (Einstein–Feynman–Maxwell–Wright) and its physical interpretations originate with Matthew Chenoweth Wright. This WNS formalization treats the residual recurrence as conventional EWMA mathematics; these results do not establish novelty or validate the broader EFMW ontology.

## Model
Real arithmetic, fixed coefficient λ, arbitrary residual stream:
m(n+1) = λ m(n) + (1−λ) r(n).
For boundedness and disturbance bounds, 0 ≤ λ ≤ 1.

## Proof obligations
- update_difference
- update_constant_error
- update_interval
- update_bounded
- track_bounded
- initial_difference
- initial_distance
- constant_error
- constant_distance
- constant_converges
- initial_difference_converges
- disturbance_bound
- monitor_preserves_protected
- monitor_preserves_grants
- monitor_preserves_history
- warning_without_grant_denied
- warning_without_grant_preserves

The library proves interval preservation, uniform residual bounds, exact geometric forgetting of initial conditions, exact constant-input error, and a finite-horizon input disturbance bound. It proves that the defined monitor ingestion operation preserves protected state, stored grants and history; an empty-grant execution remains rejected.

## Reproduce
Pinned Lean 4.19.0; mathlib release v4.19.0.
```sh
cd formal/efmw-core
lake update
lake exe cache get
lake build
lake env lean Audit.lean
```

## Boundaries
No physical law, detector superiority, warning-period formula, calibration, empirical performance or runtime refinement is proved. The geometric error formula and analytic convergence for 0 ≤ λ < 1 are proved. Real arithmetic does not establish floating-point behavior. The monitor boundary covers the defined operation, not arbitrary programs.
The recorded WNS EFMW v0.2 pilot failed its validation gate; its holdout stayed sealed. These proofs do not change that result.
This branch is stacked on integrated formal closure commit 44bbfd1af4c687e5f9780f5247051a11e24a5d6e.
