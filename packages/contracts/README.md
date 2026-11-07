# `packages/contracts` (trust domain: contracts)

Schemas, canonicalization, and frozen data shapes. Under
[UADR-0001](../../governance/adr/UADR-0001-trust-domain-layout.md) this domain imports
nothing else in the project and nothing outside the Python standard library. `tools/check_trust_domains.py` enforces that in `pytest`.

Contracts define data rules only. They grant no authority and create no evidence.

| Module | What it is | Spec | Evidence here |
|---|---|---|---|
| `weaver_contracts.canonical` | WX-CJSON-1 canonical JSON (RFC 8785, integer-only) | [`WX-CJSON-1`](../../governance/specs/WX-CJSON-1.md) | R2[self]: 19 valid + 14 reject vectors, cross-checked against `rfc8785` |
| `weaver_contracts.receipt` | wx-receipt-1 commit receipt contract | [`WX-RECEIPT-1`](../../governance/specs/WX-RECEIPT-1.md) | R2[self] for the contract; no ledger issues it yet |
| `weaver_contracts.pg001r` | PG-001R promotion-request contracts | Lumen-Nexus `governance/specs/PG-001R.md` | R2[self] here since step 4 (see below) |
| `weaver_contracts.ledger` | Root heads, Chronicle Root, `wx-chronicle-anchor-1` | [`WX-RECEIPT-LEDGER-1`](../../governance/specs/WX-RECEIPT-LEDGER-1.md) | R2[self] |
| `weaver_contracts.gate` | `Proposal`, `AuthorizationDecision` | [`WX-EXECUTION-GATE-1`](../../governance/specs/WX-EXECUTION-GATE-1.md) | R2[self] |
| `weaver_contracts.replay` | `ReplayCacheProtocol`, `generate_replay_key` | `docs/triadic-controls/ARCHITECTURE.md` | R2[self]; moved from `triadic_controls/crypto/replay.py` |

## Provenance: `pg001r.py`

Moved verbatim from `ryansctt1994-sudo/Lumen-Nexus` at
`93689d7`, `packages/contracts/lumen_contracts/pg001r.py` (MIT, same owner).
Its SHA-256, `37e3fb44b1b0d75bf821d3a98ba837a95a7baa41c28e466da118f63494b6ff8f`, matches the
Nexus `pg-001r-source-manifest.json` entry, and `tests/contracts/test_pg001r_contracts.py`
asserts that it still does. Ruff's `UP035`/`UP037` are ignored for this one file so it can
stay byte-identical.

Under outline §7, moved code arrives at R1 in its new location. In step 4 the evaluator and the
canonical 19-test conformance suite moved too and pass here, so PG-001R is R2[self] in this
repository on its own evidence, not by inheritance from Lumen-Nexus.

## Running

```bash
pytest -q tests/contracts
python -m tools.check_trust_domains
```
