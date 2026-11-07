# `packages/verifier` (trust domain: verifier)

Verification. Under [UADR-0001](../../governance/adr/UADR-0001-trust-domain-layout.md)
this domain may import only `contracts` and no I/O-capable standard-library module, so it cannot
reach runtime code to append, latch, or repair anything. `tools/check_trust_domains.py` enforces that in `pytest`.

| Module | What it is | Spec | Evidence here |
|---|---|---|---|
| `weaver_verifier.ledger` | `verify_snapshot(snapshot, anchor=None)` for ReceiptLedger snapshots | [`WX-RECEIPT-LEDGER-1`](../../governance/specs/WX-RECEIPT-LEDGER-1.md) | R2[self] |
| `weaver_verifier.crypto` | `CryptoVerifier`: Ed25519 envelopes, pinned-root key registry, roles, quorum, replay | `docs/triadic-controls/ARCHITECTURE.md` | R2[self]; moved from `triadic_controls/crypto/verifier.py` |
| `weaver_verifier.claim_transition` | A1 claim-state transition rule | `docs/A1_TRANSITION_INVARIANT.md` | R2[self]; moved from `policy/claim_transition.py` |
| `weaver_verifier.pg001r` | PG-001R promotion-gate evaluator | Lumen-Nexus `governance/specs/PG-001R.md` | R2[self] here: 19-test conformance suite passes in this repository |

## Effects

`CryptoVerifier` records replay keys, so it is not side-effect free. Its only write path is the
`ReplayCacheProtocol` object the caller passes in (`weaver_runtime.replay_cache` provides the
implementations). The verifier domain itself holds no state and imports no I/O-capable module.
`tools/check_trust_domains.py` enforces the second part with `IO_CAPABLE_IMPORT`.

## Provenance: `pg001r.py`

Moved from `ryansctt1994-sudo/Lumen-Nexus` (MIT, same owner), `packages/verifier/lumen_verifier/pg001r.py`,
together with its conformance suite (now `tests/verifier/test_pg001r_conformance.py`). Only the
import lines, the CLI usage string, and one `# type: ignore[arg-type]` in the suite's helper
(this repository type-checks tests with `mypy .`; Lumen-Nexus does not) changed.
`tests/verifier/test_pg001r_identity.py` reverses exactly those edits and checks the Nexus
source-manifest SHA-256 of both files.

Without an anchor, a verdict covers internal consistency only. Truncation and full rewrites
need an anchor held outside the operator's control, and the verdict says so.
