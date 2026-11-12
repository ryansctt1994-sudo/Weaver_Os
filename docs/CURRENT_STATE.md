# Current-state manifest

Snapshot source: `7f839efad8c273b979678b0f94e5b1175136b0ab`. This is the repository implementation index for WVR-003, not a release receipt, security audit, or promotion decision. It supersedes no historical evidence. Paths below are interpreted at this source commit; later changes require reconciliation.

## Standing and ownership

E2 / R2[self]; W0; O0_WITHHELD. Production authority is not earned. [Portfolio status](../PORTFOLIO_STATUS.md) governs portfolio standing; [contradictions](../governance/CONTRADICTIONS.yaml) records unresolved obligations; [release readiness](RELEASE_READINESS.md) owns release requirements. Historical receipts remain bound to their recorded commit and host.

IMPLEMENTED means executable source exists, not that every behavior is proved. SIMULATION ONLY excludes physical validation. PLACEHOLDER has no implementation. DEFERRED points to a separately bounded historical artifact. Validation links below identify tests or evidence documentation, not an assertion that every listed component has exhaustive coverage.

## Component map

| Component | Source | Validation or limitations | State | Boundary |
| --- | --- | --- | --- | --- |
| Contracts | [source](../packages/contracts/weaver_contracts) | [reference](../tests/contracts) | IMPLEMENTED | Canonical serialization, receipts and proposals; legacy serializers remain C-CANON-001. |
| Authorization verifier | [source](../packages/verifier/weaver_verifier/crypto.py) | [reference](../tests/triadic_controls) | IMPLEMENTED | Signatures, roles, scope, quorum and signing-policy checks; production integration not established. |
| Execution gate | [source](../packages/runtime/weaver_runtime/gate.py) | [reference](../tests/gate) | IMPLEMENTED | Pinned proposals and repeated authorization; no external-effect confinement; C-GATE-001 and #120 remain open. |
| Receipt ledger | [source](../packages/runtime/weaver_runtime/ledger.py) | [reference](../tests/ledger) | IMPLEMENTED | SQLite dual ledger; internal consistency requires external anchors for stronger authenticity claims. |
| Replay storage | [source](../packages/runtime/weaver_runtime/replay_cache.py) | [reference](../tests/triadic_controls/test_sqlite_replay.py) | IMPLEMENTED | SQLite uniqueness and persistence; multi-process/crash acceptance remains open. |
| Registry rollback | [source](../packages/runtime/weaver_runtime/registry_sequence.py) | [reference](../tests/triadic_controls/test_registry_rollback.py) | IMPLEMENTED | Opt-in shared-store high-water marks; trust on first use; schema decision #121 open. |
| State reconstruction | [source](../packages/verifier/weaver_verifier/state.py) | [reference](../tests/state) | IMPLEMENTED | In-tree projection differs from RC1; does not silently supersede frozen RC1 evidence. |
| Promotion gate | [source](../packages/verifier/weaver_verifier/pg001r.py) | [reference](../tests/verifier) | IMPLEMENTED | PG-001R eligibility is not an authority grant or recovery of historical PG-001. |
| Checkpoint witness | [source](../packages/witness/weaver_witness/witness.py) | [reference](../tests/custody) | IMPLEMENTED | Reference witness; independent custody NOT ESTABLISHED (C-CUSTODY-001). |
| Hardware veto | [source](../hardware/lucifer_latch) | [reference](../tests/hardware) | SIMULATION ONLY | RTL and Python twin; no physical interlock validation. |
| Release guard | [source](../src/weaver_release_guard) | [reference](../docs/RELEASE_READINESS.md) | IMPLEMENTED | Provenance CLI; help smoke is not full behavioral coverage; artifact retention remains blocked. |
| Verification runner | [source](../tools/verify_all.py) | [reference](../docs/VERIFICATION_INFRASTRUCTURE.md) | IMPLEMENTED | Seven required verifiers; publisher-controlled CI is not independent reproduction. |
| Residual monitor | [source](../compression/residual_monitor.py) | No component validation claimed | PLACEHOLDER | TODO only. |
| Policy adapter | [source](../policy/signed_verifier_adapter.py) | No component validation claimed | PLACEHOLDER | No implemented verifier-to-execution authorizer adapter here. |
| Legacy policy gate | [source](../policy/policy_gate.py) | No component validation claimed | PLACEHOLDER | Use the explicit implemented contracts and verifier modules; this file is not enforcement. |
| Legacy Chronicle/kernel/receipts | [source](../chronicle) | No component validation claimed | DEFERRED | chronicle/, kernel/ and receipt/ defer to the bound RC1 witness; successors have distinct scopes. |

## Integration boundary

The execution gate asks its authorizer repeatedly. CryptoVerifier consumes replay state during verification and cannot be passed directly as that authorizer. A future adapter must verify once, bind the decision to the proposal, and answer later expiry/revocation queries. Persistent stores and controlled external effects need explicit integration. Source: [gate contract and implementation](../packages/runtime/weaver_runtime/gate.py).

Import restrictions are checked by [check_trust_domains](../tools/check_trust_domains.py); they are not a hostile-code sandbox. Protocol-injected replay and registry stores can perform writes even though verifier imports are restricted.

## Current code versus historical plans

- Existing package domains: contracts, runtime, verifier, witness.
- Learning and adapters are planned domains, not implemented packages in this snapshot. Release guard exists under src/, not packages/release_guard/.
- [Unified outline](architecture/UNIFIED_SYSTEM_OUTLINE.md) contains conceptual and historical statements; use this map and the actual source for implementation presence.
- triadic_controls/crypto/ and policy/claim_transition.py are compatibility shims; the triad ledger remains separate.
- The [RC1 release](../releases/weaver-witness-signed-rc1/README.md) remains frozen evidence, not evidence automatically transferred to the newer state projection.
- #118 proposal integrity, #119 registry rollback, #122 signing policy and #123 historical release reconciliation are merged in this snapshot. #120 and #121 remain open design obligations. This is not an exhaustive reconciliation of inherited PRs (WVR-004).

## Validation and next gates

The canonical command is make verify with requirements-verification.lock; see [verification infrastructure](VERIFICATION_INFRASTRUCTURE.md). Check exact source/head versus tested merge identity when reading CI. A passing gate does not establish independent custody, production authority, hermetic builds, or full-system formal verification.

Next acceptance work: proposal binding and authorization adapter; multi-process and crash replay tests; retained release artifacts paired with digests; independent reproduction and checkpoint custody. C-CANON-001, C-RCPT-001, C-GATE-001, C-CUSTODY-001 and C-DUAL-001 must retain their recorded dispositions until their own closure obligations are met.

## Maintenance rule

When implementation, validation scope, or a contradiction disposition changes, update the source snapshot and affected rows together. Preserve old receipts; do not relabel their commit. Opening or merging a PR alone does not close a backlog item or raise evidence standing.
