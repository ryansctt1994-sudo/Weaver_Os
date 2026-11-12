# Gate Zero — Repository Enforcement Contract

**Policy ID:** `WEAVER-GATE-ZERO-1`  
**Status:** DECLARED · NOT YET SERVER-ENFORCED

Gate Zero is the repository-level control that turns the portfolio's governance doctrine into a GitHub workflow discipline.

## Required policy

The canonical `main` branch is intended to require:

1. pull requests for changes;
2. no force pushes;
3. no branch deletion;
4. linear history;
5. required status checks before merge;
6. candidate pull-request state to remain non-authoritative until merge.

## Required checks

The repository must retain and run these workflow families:

- CI
- tests
- triadic-controls CI
- Verification evidence
- Witness TLA model
- Gate Zero self-check

The machine-readable declaration is in `governance/gate-zero.json`.

## Important boundary

This repository can declare and test the expected policy, but a checked-in file cannot configure GitHub's server-side branch protection by itself.

Therefore:

[
\boxed{DeclaredGovernance \neq ServerEnforcedGovernance}
]

A Gate Zero declaration is not evidence that GitHub is enforcing it. Server-side protection must be configured separately and then independently inspected.

## Promotion rule

Open or draft pull requests remain candidate state.

[
\boxed{CandidatePRState \neq CanonicalMainState}
]

A green pull request may support merge review. It does not become canonical portfolio state until merged to the canonical branch.

## Failure behavior

The Gate Zero workflow fails if required governance files or workflow files disappear, or if the machine-readable declaration becomes malformed or internally inconsistent.

That workflow does **not** substitute for branch protection. Its purpose is to make drift visible.
