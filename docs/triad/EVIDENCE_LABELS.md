# Evidence Label Discipline

Weaver / Triad uses explicit evidence labels to prevent architecture, reports, and code claims from being silently promoted beyond their proof.

## Canonical Labels

`HYPOTHESIS`

A proposed invariant, mechanism, or safeguard that has not yet been exercised in a reproducible implementation.

`REPORTED`

Claimed or described as existing, but not independently verified from this repository state.

`VERIFIED-LOCAL`

Observed in a local run, but not yet supported by repository-level deterministic instructions, committed tests, or reviewable receipts.

`VERIFIED-REPO`

Supported by committed code, deterministic instructions, and reproducible tests or validation artifacts in this repository.

`FAILED`

Tested and did not satisfy the claimed behavior.

`SUPERSEDED`

Previously used claim, artifact, or mechanism replaced by a newer version.

`UNVERIFIED`

Present but not evaluated.

## Promotion Rule

No claim may move to a stronger label without a receipt or deterministic reproduction path.

## Downgrade Rule

Any claim whose reproduction path breaks must be downgraded until replay, tests, or receipts restore the evidence boundary.

## Required Use

Evidence labels must be used in handoffs, runbooks, audit notes, README claims, and release notes whenever an artifact is described as implemented, verified, or production-relevant.
