# `packages/verifier` (trust domain: verifier)

Read-only checks. Under [UADR-0001](../../governance/adr/UADR-0001-trust-domain-layout.md)
this domain may import only `contracts`, so it cannot reach runtime code to append, latch,
or repair anything. `tools/check_trust_domains.py` enforces that in `pytest`.

| Module | What it is | Spec | Evidence here |
|---|---|---|---|
| `weaver_verifier.ledger` | `verify_snapshot(snapshot, anchor=None)` for ReceiptLedger snapshots | [`WX-RECEIPT-LEDGER-1`](../../governance/specs/WX-RECEIPT-LEDGER-1.md) | R2[self] |

Without an anchor, a verdict covers internal consistency only. Truncation and full rewrites
need an anchor held outside the operator's control, and the verdict says so.
