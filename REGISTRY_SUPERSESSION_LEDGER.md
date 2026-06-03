# Registry Supersession Ledger

Purpose: record when a registry, doctrine, checklist, or handoff supersedes an earlier artifact.

A supersession does not erase history. It records lineage and prevents stale documents from silently retaining authority.

## Current Baseline

| Date | New Baseline | Supersedes | Status | Notes |
|---|---|---|---|---|
| 2026-06-03 | `docs/HANDOFF_vFINAL.md` | Prior conversational handoff fragments | PRE-PRODUCTION BASELINE | Evidence ceiling remains L3 until independent replay. |
| 2026-06-03 | `REGISTRY.md` | Informal inventory notes | PRE-PRODUCTION REGISTRY | Applies evidence labels to repository and Cathedral Mesh claims. |
| 2026-06-03 | `INVARIANTS.md` | Scattered invariant statements | DOCTRINE BASELINE | Does not by itself verify implementation. |
| 2026-06-03 | `CLAIM_DOWNGRADE_LOG.md` | Ad hoc downgrade discussion | AUDIT BASELINE | Captures claim reductions and promotion requirements. |
| 2026-06-03 | `MVP0_REPLAY_CHECKLIST.md` | General next-step recommendations | EXECUTION CHECKLIST | Defines the next legitimate authority upgrade. |

## Supersession Rule

A newer document supersedes an older document only when it states what it supersedes and preserves downgrade lineage. Silent replacement is prohibited.

## Stale Document Handling

Older documents should be marked one of:

- SUPERSEDED
- ARCHIVAL / NON-AUTHORITY
- REFERENCE ONLY
- ACTIVE BASELINE

## Promotion Rule

No supersession can promote an implementation claim above its evidence receipts. Documentation cannot upgrade code maturity by declaration.
