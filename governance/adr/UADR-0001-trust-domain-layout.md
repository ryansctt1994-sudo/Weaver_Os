# UADR-0001: Unified trust-domain layout and import rules

- **Status:** ACCEPTED by [GD-0001](../decisions/GD-0001.md) (single steward; `C-DUAL-001` limitation recorded)
- **Date:** 2026-11-07
- **Decision authority:** GD-0001, D3
- **Enforcement:** `python -m tools.check_trust_domains` (also run by `pytest`)
- **Numbering:** `UADR-` is used so this record does not collide with Lumen-Nexus `ADR-0006`
  when the Nexus governance records are merged in.

## Context

Weaver_Os is the portfolio anchor, but its trust boundaries are implicit. Lumen-Nexus
already separates `contracts / runtime / verifier` and rejects cross-domain imports in CI.
The unified outline (§4) adopts that model and adds four domains for code arriving from
Weaver and Lumen.

## Decision

Each directory directly under `packages/` is a trust domain:

| Domain | May import | Holds |
|---|---|---|
| `contracts` | nothing in the project | schemas, frozen dataclasses, canonicalization profile |
| `runtime` | `contracts` | ReceiptLedger, replay cache, execution gate (stateful) |
| `verifier` | `contracts` | PG-001R, CryptoVerifier, claim transition, replay verify (read-only) |
| `learning` | `contracts`, `runtime` | continual-learning pipeline; promotion goes through `verifier` decisions passed in as data |
| `release_guard` | `contracts` | SLSA / OIDC provenance |
| `adapters` | `contracts` | FreeLattice, provider mesh, skill manifests: may only build proposals |

Non-runtime zones at the repository root, `research/`, `archive/`, `legacy/` and
`evidence/`, may never be imported from `packages/`.

The rules fail closed:

- an import from a domain that is not listed as allowed is a violation;
- an import from a non-runtime zone is a violation;
- a directory under `packages/` that is not in the table is a violation;
- a file that cannot be parsed is a violation;
- `importlib.import_module("…")` and `__import__("…")` with literal names are checked too.

Added in outline step 4 (same ratified layout, stricter enforcement; the checker also has its own CI step):

- `contracts` may import only the Python standard library (`NON_STDLIB_IMPORT`);
- `contracts` and `verifier` may not import process, network, or database modules such as
  `sqlite3`, `subprocess`, `socket`, `urllib` (`IO_CAPABLE_IMPORT`);
- no `json.dumps(..., sort_keys=True)` under `packages/` outside a named allowlist
  (`LEGACY_CANONICALIZER`), and an allowlist entry whose file no longer needs it fails (`STALE_ALLOWLIST`).

Today `packages/` does not exist, and the checker reports that and passes. The rules apply
as soon as the first package moves in (outline step 2).

## Why `verifier` may not import `runtime`

Verification must stay read-only. If the verifier can reach the ledger's code, it can
mutate the ledger. This is the same reasoning as Nexus's checker and ADR-0006's
"verification remains read-only and cannot latch, execute, or repair the ledger".

## Why `learning` may import `runtime` but not `verifier`

Learning reads chronicled experience, which is runtime state. It must not call the
promotion gate itself, because that would let it choose when it is evaluated. Gate
decisions reach it as data produced elsewhere.

## Known limits

- The checker sees static and literal dynamic imports. It does not see imports built from
  computed strings, `exec`, or path manipulation. Review still has to cover those.
- Top-level Weaver modules outside `packages/` are not covered. After step 4, `triadic_controls/crypto/*`
  and `policy/claim_transition.py` are re-export shims. `triadic_controls/ledger.py` (the triad ledger),
  `tools/`, and the other top-level modules have not moved.

## Consequences

Moving code into `packages/` becomes a step with a checkable boundary. Each move has to
pass this checker and its own tests in the new location before it is re-labelled R2
(outline §7).
