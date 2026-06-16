# PR #25 Audit Directive

## Purpose

PR #25 bootstraps the existing Weaver OS verification spine into the broader Weaver Governance Runtime structure.

The audit objective is not to add more architecture. The objective is to determine whether the new governance documents accurately describe the current implementation and what must be built before E3 can be claimed.

## Required Audit Scope

Audit the following existing implementation areas:

```text
triadic_controls/
src/weaver_release_guard/
tests/
docs/PROMOTION_RULES.md
pyproject.toml
```

Audit the following new governance areas:

```text
README.md
GOVERNANCE.md
ROADMAP.md
constitution/CONSTITUTIONAL_INVARIANTS.md
manifests/MUST_KEEP_REGISTRY.v1.json
schemas/receipt.schema.json
validation/CROSS_SYSTEM_VALIDATION_AGENDA.md
```

## Audit Questions

1. Which README claims are supported by executable code?
2. Which governance claims are specification-only?
3. Which schema fields are not emitted by any workflow?
4. Which authority terms are inconsistent across docs and code?
5. Which claims must be demoted to avoid overstating evidence?
6. What is the minimum change set required to produce a Gate 1 execution receipt?

## Required Output

Create an audit report with four sections:

```text
PASS
GAP
BLOCKER
DO_NOT_CLAIM
```

## E3 Boundary

PR #25 does not claim E3.

E3 requires at minimum:

- existing tests executed through a receipt-producing workflow,
- command and exit code recorded,
- stdout and stderr hashed,
- source manifest emitted,
- receipt schema conformance checked,
- authority_earned=false,
- production_allowed=false,
- replay receipt generated or explicitly marked pending.

## Explicit Non-Goals

Do not add new architecture.

Do not add new layers.

Do not start Delta717 experiments yet.

Do not claim formal verification.

Do not mark the PR ready for review until audit and Gate 1 receipts exist.
