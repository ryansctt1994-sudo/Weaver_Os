# `packages/runtime` (trust domain: runtime)

Stateful components. Under [UADR-0001](../../governance/adr/UADR-0001-trust-domain-layout.md)
this domain may import only `contracts`.

| Module | What it is | Spec | Evidence here |
|---|---|---|---|
| `weaver_runtime.ledger` | `ReceiptLedger`: single-owner, SQLite-backed Dual Ledger (Lumen-Nexus ADR-0006, accepted by GD-0002) | [`WX-RECEIPT-LEDGER-1`](../../governance/specs/WX-RECEIPT-LEDGER-1.md) | R2[self] |
| `weaver_runtime.replay_cache` | `InMemoryReplayCache` (tests and simulation only) and `SQLiteReplayCache` | `docs/triadic-controls/ARCHITECTURE.md` | R2[self]; moved from `triadic_controls/crypto/` |

```python
from weaver_runtime.ledger import ReceiptLedger

with ReceiptLedger("ledger.db", ledger_id="wx-main") as ledger:
    receipt = ledger.admit("STATE_TRANSITION", {"to": "EXECUTED"},
                           actor_id="op-1", policy_version="policy-v1")
    ledger.reject("PROMOTION", {"to": "R4"}, actor_id="op-2",
                  policy_version="policy-v1", reason_code="NO_WITNESS")
    anchor = ledger.anchor().to_dict()   # publish somewhere the operator cannot rewrite
    snapshot = ledger.snapshot()         # hand to weaver_verifier.ledger.verify_snapshot
```

The ledger records gate decisions; it does not make them.
