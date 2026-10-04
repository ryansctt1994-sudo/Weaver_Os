# Weaver activation durable recovery contract v0.1

Status: specification candidate; no WAL or persistence implementation is added.
Base runtime: PR #65, commit `8db6965aa6341a07828f17bdd0d30ca11caf545b`.

## Guarantee and scope

Once an execution intent is durable, uncertainty cannot make its request ID
eligible for automatic dispatch again. A replacement ID for the same operation
requires separately authorized reconciliation or a duplicate-effect waiver.
Loss of progress is permitted. Exactly-once physical effects and unconditional
liveness are not guaranteed.

`WeaverRecovery.tla` models two ordered IDs for one semantic operation: R1 is
the original and R2 a replacement after an indeterminate outcome. Valid external
authority is assumed for both. The model is separate from `WeaverActivation.tla`;
no composition or runtime-refinement theorem is claimed.

## Identity and storage envelope

Bind each intent to request ID, stable operation key, authority-event reference,
activation contract digest, backend identity/binary digest, checkpoint digest,
input digest, and retention constraints. New nonces must not bypass operation
identity. Determining equivalent physical effects is a caller/backend contract;
a hash cannot infer it. Cross-key aliases need additional policy.

A durable envelope must bind schema, writer/fencing epoch, sequence, previous
record digest, record kind, and canonical payload digest. Hashes alone do not
authenticate records or detect coordinated rollback. The model abstracts these
identities and does not implement their storage or cryptography.

## Persistence boundaries

| Transition | Contract |
| --- | --- |
| Admit → buffer intent | Verify authority and exact identity; do not dispatch. |
| Buffer → fsync intent | Consume ID when durable; dispatch requires successful flush and a live admitted slot. |
| Dispatch → buffer result | Preserve actual outcome; REJECT may follow physical effects. |
| Buffer result → fsync terminal | Make receipt durable before acknowledging its durable outcome. |
| Crash → boot | Drop volatile dispatch eligibility; replay before admitting work. |
| Unclosed intent → stage recovery | Derive CRASH_INDETERMINATE / EXECUTION_OUTCOME_UNKNOWN. |
| Stage → fsync recovery | Preserve consumed ID and deny automatic redispatch. |
| Recovery → online | No unclosed intents remain; ownership/fencing is established. |

Chronicle publication is a separate idempotent projection keyed by durable
record ID. A crash after receipt fsync but before publication republishes that
record, never the capability. This projection is an implementation obligation,
not modeled by this bounded state space.

## Unknown outcomes and repeatable recovery

An unclosed intent is consistent with zero, partial, or completed execution.
Write a separate recovery disposition, not a synthetic execution PASS/REJECT:

- disposition: `CRASH_INDETERMINATE`
- reason: `EXECUTION_OUTCOME_UNKNOWN`
- consumed: true; automatic redispatch: denied
- reference: exact original durable intent identity

Derive the disposition's semantic ID deterministically from the intent and
recovery schema. A scan timestamp must not manufacture a new terminal result.
Subsequent observations may record scans without changing the disposition.

`Normalize` maps Intent to Indeterminate and preserves other dispositions.
The model checks `Normalize(Normalize(d)) = Normalize(d)` and allows crashes
between recovery staging and fsync. Eventual completion additionally requires a
crash-free interval, successful storage and fair scheduling. Semantic idempotence
does not prove unconditional convergence during infinitely repeated crashes.

## Four recovery invariants

| Property | Model predicate |
| --- | --- |
| Durable intent precedes dispatch | `Inv_DurableBeforeDispatch` |
| Unknown requests remain terminal; at most one dispatch per ID | `Inv_UnknownNeverRedispatched` |
| Durable recovery normalization is idempotent and does not invent intent | `Inv_RecoveryIdempotent` |
| Recovery creates no authority | `Inv_NoAuthorityGain` |

Additional invariants require bound resolution for replacement R2 and an actual
dispatch before a normal terminal receipt.

## Replacement request requirements

Fresh authority is necessary but insufficient. Require an independently
authorized decision bound to R1, operation key, issuer, evidence, scope and
freshness. It must establish either:

1. Reconciled: no duplicate-relevant effects AND no live/delayed prior worker.
   Showing only that execution did not complete is insufficient.
2. Waived: explicit acceptance of possible duplicate physical effects.

Neither decision erases R1's unknown outcome or permits its ID to dispatch again.
The model treats these decisions as trusted external facts. It does not verify
signatures, issuers or backend evidence. A waiver may permit two physical
attempts under different IDs; no operation-wide exactly-once claim follows.

## Storage assumptions and review gates

`CrashChoices` allows complete unacknowledged buffers to survive OR disappear:
intent, terminal receipt, and recovery disposition. A survived valid intent is
consumed even without a recorded fsync acknowledgment. Previously acknowledged
durable records persist in this abstraction. Records are atomic and valid.

Before implementing persistence:

- Define filesystem/device flush, rename and directory-fsync guarantees.
- Validate framing, digests, sequence and identity on replay. Torn, corrupt,
  conflicting or untrusted history must quarantine/fail closed, never establish
  that a request ID is unused. Torn writes are outside the present model.
- Establish exclusive ownership and fence stale workers. Model Crash stops its
  executor; surviving subprocesses or remote capabilities need stronger fencing.
- Reconcile receipts with exact intents and external anchors. Whole-store
  rewriting or rollback is outside the bounded model.
- Make recovery and Chronicle publication retries incapable of dispatch.
- Inject faults at every write/flush/dispatch/ack boundary before claiming that
  a storage implementation refines this contract.

## Reproduction and sensitivity

```
python -m tools.fetch_tlc /tmp/tla2tools.jar
python -m tools.check_recovery_model /tmp/tla2tools.jar --output verification-output/recovery
```

The runner retains hashed models, configurations and logs. Four mutations must
violate named invariants: dispatch before fsync, fresh-nonce bypass, fabricated
execution REJECT during recovery, and non-idempotent normalization. Three
reachability probes produce counterexamples showing indeterminate outcomes with
zero, partial and completed execution. They establish only those named results,
not blanket non-vacuity or correctness of a persistence implementation.

## Predecessor qualification

PR #65 source head `8db6965aa6341a07828f17bdd0d30ca11caf545b` passed six
workflows and nine jobs. The verification workflow checked GitHub's merge commit
`afc1c6551160fb4fd448dda27bb3378bf2eceb79` against base
`ee725f7cf923d86d915900fc93ef2e3f6e5eef1c`; these identities are distinct.

- tests: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871875
- verification: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871920
- Witness TLA: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871825
- Activation TLA: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871809
- triadic controls: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871812
- CI: https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37190871803

These runs qualify the predecessor, not this new specification or Lean package.
The Formal foundations workflow independently qualifies the new sources and
retains their verified commit and hashes.
