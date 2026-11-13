# Status Ledger Alignment

Status: E1 SPEC / CONTINUITY ARTIFACT

This document maps the Cathedral-Sentinel-Weaver maturity vocabulary to the QGS evidence ladder.

## Doctrine

Implementation is not verification.
CI configuration is not CI passage.
Documentation is not proof.
Dashboard status is not authority unless receipts exist.

## Evidence Ladder

| Evidence Class | Status Ledger Taxonomy | Execution Definition |
|---|---|---|
| E0 | CLAIM | Untested theoretical proposition. |
| E1 | SPEC | Documented schema, architecture, or threat model. |
| E2 | SIMULATED | Tests or CI validation in memory, mock, or local simulated context. |
| E3 | RECEIPTED | Cryptographically bound to an operational payload or recorded execution receipt. |
| E4 | REPLICATED | Deterministically reproduced across multiple environments or operators. |
| E5 | AUDITED | Witnessed, signed, and externally verified. |

## Canonical Terms

Use:

```text
IMPLEMENTED
PENDING
OPEN GAP
RECEIPT REQUIRED
RECEIPTED
REPLICATED
AUDITED
```

Avoid unsupported claims such as:

```text
production-ready
verified
safe
complete
sealed
release candidate
```

unless the corresponding receipt tier exists.

## Current Weaver Status

```text
IMPLEMENTED / DEVELOPMENT VERIFICATION SPINE / PENDING RECEIPTS
```

This means code and documents exist, but release readiness is not established until evidence is recorded.
