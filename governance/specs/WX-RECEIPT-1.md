# wx-receipt-1: ReceiptLedger Commit Receipt

**Status:** SPECIFIED + IMPLEMENTED as a contract (`weaver_contracts.receipt`); no ledger issues it yet
**Evidence:** R2[self] for the contract only
**Authority:** O0
**Outline step:** 2 (§5.2). The issuing ReceiptLedger is step 3.

## Purpose

One receipt records that one event was committed to one root of the Dual Ledger. Under
ADR-0006 (Lumen-Nexus) the ledger alone assigns `sequence` and `predecessor_digest` and
creates the receipt after a successful commit. Callers never build receipts.

## Fields

| Field | Rule |
|---|---|
| `schema` | `"wx-receipt-1"` |
| `canonicalization` | `"WX-CJSON-1"` |
| `ledger_id` | identifier |
| `root` | `AUTHORITY` or `REJECTION` |
| `sequence` | integer ≥ 0 |
| `predecessor_digest` | SHA-256 hex; equal to 64 zeros **exactly when** `sequence` is 0 |
| `event_type` | `UPPER_SNAKE` token |
| `event_digest` | SHA-256 hex of the WX-CJSON-1 canonical event content |
| `actor_id`, `policy_version` | identifiers, not placeholders |
| `admissibility` | `AUTHORITY` → `ADMITTED` only; `REJECTION` → `REJECTED` or `QUARANTINED` |
| `reason_code` | `null` when `ADMITTED`; required `UPPER_SNAKE` token otherwise |
| `committed_at` | UTC, `YYYY-MM-DDTHH:MM:SSZ` (no offsets, no fractions) |
| `receipt_digest` | SHA-256 of the canonical receipt **without** this field |

Unknown or missing fields are rejected. A receipt whose digest does not match its body cannot
be constructed. The JSON Schema `schemas/wx_receipt_1.schema.json` covers structure. The
cross-field rules above are enforced by the contract.

## Invariants carried in the shape

- `FAILED_ACTIONS_ARE_NOT_STATE`: a rejected or quarantined event cannot sit on the Authority Root.
- `FAILED_ACTIONS_ARE_EVIDENCE`: the Rejection Root has the same receipt shape, so every
  denial produces a receipt.
- `GENESIS_IS_DECLARED_NOT_VERIFIED`: sequence 0 carries the visible all-zero predecessor.

## Deliberately excluded

- `replay_result` / `verifier_id` (from Lumen's receipt): replay is a later act by a read-only
  verifier and produces its own record.
- Signatures: `receipt_digest` gives integrity only. A signed profile is blocked on
  Lumen-Nexus #13 and `C-RCPT-001`.

## Relationship to existing files

`schemas/receipt.v1.json` is an empty schema (`{}`) that accepts anything, and
`tests/test_receipt_schema.py` is a TODO stub. Both are recorded under `C-STUB-001` and are
superseded by this contract for new work.
