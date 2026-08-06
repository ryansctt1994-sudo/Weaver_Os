# Promotion Gate

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

This directory defines promotion controls only. It does not authorize runtime execution.

## Non-negotiable boundary

```text
capability != authorization
architecture != authority
specification != implementation
declared_success != replay_verified_success
```

## Promotion rule

A component remains at `HOLD` until it has:

1. pinned source provenance,
2. passing deterministic tests,
3. tamper-evident receipts,
4. replay verification,
5. no unresolved critical/high Strix findings,
6. explicit authority lease status allowing the requested action,
7. independent witness evidence before any E4 claim.

## Blocks

Promotion is blocked by default when:

- runtime code is invoked outside the governance wrapper,
- an external skill is installed without an intake receipt,
- a receipt chain breaks,
- replay cannot reproduce the decision,
- Strix emits unresolved critical/high findings,
- RosClaw leaves simulation-only mode,
- a component attempts to self-promote.

## Current status

```text
PROMOTION_GATE: HOLD
PRODUCTION_AUTHORITY: NONE
PHYSICAL_ACTUATION: BLOCKED_BY_DEFAULT
WITNESS_STATUS: PENDING
```
