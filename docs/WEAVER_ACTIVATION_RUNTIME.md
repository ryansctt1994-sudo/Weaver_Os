# Weaver Activation Runtime

Status: Weaver-owned reference implementation candidate. No authority, evidence-tier, or production promotion is implied.

The Weaver Activation Runtime is the native capability layer below the existing Weaver authority boundary. It is not imported from, dependent on, or delegated to another architecture.

## Contract

Every activation is represented by the frozen, versioned contract `weaver-activation-contract-1`.

The signed contract binds request identity, model identity, action, backend identity, the exact native backend artifact SHA-256 when native execution is used, checkpoint SHA-256, input SHA-256, retention floor, and a canonical contract SHA-256.

A valid token for any different contract is rejected.

## Execution path

```text
proposal
  -> triadic_controls cryptographic authority verification
  -> WeaverActivationAdapter
  -> versioned activation contract check
  -> duplicate-request defense
  -> Python or NativeWeaverBackend capability
  -> identity + metric + retention validation
  -> ActivationEvidence(authority_delta = 0)
  -> canonical receipt / Chronicle boundary
  -> replay / witness / adversarial verification
```

## Native ABI

The frozen native entry point is `weaver_activate_v1`.

The wrapper verifies the native library digest before load, after load, and after execution. Input bytes are hashed immediately before crossing the ABI. The backend result must echo the contract version and exact request/model/backend/checkpoint identity.

The native implementation is responsible for ensuring that the checkpoint digest named by the admitted contract is the checkpoint actually executed.

## Fail-closed rules

- unsupported contract version: reject
- malformed identity, digest, or retention floor: reject before authority verification
- invalid authority: reject before backend execution
- signed payload mismatch: reject
- duplicate request identity: reject
- backend exception or native non-zero status: reject
- backend/result identity substitution: reject
- non-finite or invalid retention metric: reject
- retention below declared floor: reject
- every evidence object: `authority_delta = 0`

Process-local duplicate suppression is defense in depth. Durable exactly-once behavior requires the persistent execution boundary.

## Non-claims

This layer does not prove model quality, consciousness, autonomy, deployment safety, or production readiness. Capability does not imply authority; evidence does not imply authority.


## Formal model

`audit-package/formal/tla+/WeaverActivation.tla` models the activation lifecycle independently from the surrounding Witness model:

```text
Proposed -> Authorized -> ContractBound -> Executed -> ResultVerified -> Recorded
      \-> Rejected
```

The bounded TLC model checks:
- execution requires prior authorization plus contract/backend/checkpoint/input binding
- the admitted authority event is mapped to one exact request/contract/backend/checkpoint/input tuple; a different tuple cannot reach `ContractBound`
- rejection codes are phase constrained, so an authority failure cannot appear after execution and a backend/result failure cannot appear before execution
- `authorityDelta` remains zero
- activation never mutates the modeled protected state
- an execution counter prevents a request from executing more than once
- every terminal rejection has rejection evidence
- PASS Chronicle evidence is admitted only from `ResultVerified` and remains bound to the request artifacts and authority event

The model intentionally uses an execution counter rather than treating membership in a consumed-request set as proof of single execution. It also models rejection evidence directly while keeping `Rejected` terminal.

This is bounded model checking of an abstraction. It is not a general refinement proof that the Python/C implementation implements every TLA+ transition exactly.

## Trace-driven correspondence

`ActivationTraceRecorder` can be attached to `WeaverActivationAdapter` without changing authority or execution semantics. It emits canonical NDJSON observations for the abstract lifecycle actions `Authorize`, `BindContract`, `Execute`, `VerifyGood`, `Reject`, and `RecordPass`.

The frozen corpus at `tests/fixtures/activation_trace_corpus.json` currently contains nine first-attempt cases:
- PASS
- contract-version mismatch
- malformed identity
- invalid authority
- authority-binding mismatch
- backend failure
- result-identity mismatch
- invalid metric
- retention-gate failure

`tools/check_activation_trace_conformance.py` executes those cases through the real Python adapter, hashes every emitted NDJSON trace, deterministically compiles each trace into `GeneratedActivationTrace.tla`, and replays it through `WeaverActivationTrace.tla`.

The wrapper checks `Inv_TraceCanAdvance`: whenever unconsumed runtime events remain, the next emitted event must correspond to an enabled `WeaverActivation` transition. This prevents an impossible runtime trace from satisfying the temporal specification merely by stuttering.

Two negative controls are mandatory:
- moving `Execute` before `BindContract` must be rejected
- changing a post-execution backend rejection into `AUTHORITY_INVALID` must be rejected

This correspondence cut is deliberately scoped. Process-local duplicate-request rejection is not included because a faithful duplicate trace requires a persisted pre-state showing that the request was previously consumed. Native checkpoint execution identity and arbitrary in-process memory integrity also remain separate obligations. The result is mechanical trace conformance for the frozen first-attempt corpus, not universal implementation refinement.

## Canonical activation receipt

`ActivationReceipt` and `schemas/activation_receipt.schema.json` define the runtime evidence envelope.

A PASS receipt requires valid SHA-256 identities for the contract, backend artifact, checkpoint, input, and output. A REJECT receipt may contain null artifact fields when rejection occurred before those fields were structurally admitted; the raw attempted request remains bound by `intent_sha256` and the supplied authority material by `authority_payload_sha256`.

The current authority verifier exposes `ledger_event_type`, not a unique ledger-event identifier. Therefore `authority_event_id` is explicitly nullable. The runtime does not invent a ledger identity from another hash.

## Runtime-integrity tripwires

The in-process native seam now:
- resolves and pins the requested shared-library path
- always fails closed on direct interposition controls such as `LD_PRELOAD`, `LD_AUDIT`, and `DYLD_INSERT_LIBRARIES`
- defaults to strict rejection when dependency search-path variables such as `LD_LIBRARY_PATH` are present; ABI conformance tests may explicitly relax that one policy when the CI runner injects a search path
- requests local/immediate symbol resolution where the platform exposes it
- on Linux, verifies that the target library is mapped from the expected path/device/inode
- rejects deleted target mappings
- rejects writable+executable mappings for the target library
- repeats the mapping check after execution
- retains file hashing before load, after load, and after execution

These checks do not prove arbitrary process-memory integrity, do not hash relocated executable pages, and cannot undo a preload/interposer that entered before the current process started. Relaxing the search-path policy for an ABI conformance test is not a production qualification. Full loader-environment sanitization requires a fresh isolated worker process started with a controlled environment. Dependency closure/RPATH/RUNPATH attestation is also not yet claimed.

### Stateful trace correspondence (bounded continuation)

Trace schema `weaver-activation-trace-2` adds `BeginAttempt` and
`TerminalReceipt`. Every attempt binds the consumed-request IDs, execution
counts, terminal state and evidence-receipt hash, and SHA-256 of the complete
prior canonical NDJSON prefix. The checker derives these values by replaying
that retained prefix and rejects altered snapshots even when their snapshot
hash is recomputed. A detached continuation is rejected.

The original `activation_trace_corpus.json` remains frozen. The separately
versioned `activation_trace_stateful_corpus.json` extends its nine scenarios with
same-adapter duplicates after PASS and BACKEND_FAILED. The trace wrapper models
retry admission and duplicate rejection separately from the original execution
lifecycle: the original terminal receipt and execution count remain unchanged.
Duplicate rejection cannot call the backend or grant authority.

This is correspondence for this bounded, single-request corpus. State is still
process-local; this does not establish durable exactly-once execution across
restart, authenticate an observer, or detect coordinated rewriting of an entire
trace and its external digest. Evidence hashes need an independently retained
anchor for that stronger threat model. This is not universal Python/C refinement.
