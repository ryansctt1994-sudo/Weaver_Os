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
- `authorityDelta` remains zero
- activation never mutates the modeled protected state
- an execution counter prevents a request from executing more than once
- every terminal rejection has rejection evidence
- PASS Chronicle evidence is admitted only from `ResultVerified` and remains bound to the request artifacts and authority event

The model intentionally uses an execution counter rather than treating membership in a consumed-request set as proof of single execution. It also models rejection evidence directly while keeping `Rejected` terminal.

This is bounded model checking of an abstraction. It is not yet a refinement proof that the Python/C implementation implements every TLA+ transition exactly.

## Canonical activation receipt

`ActivationReceipt` and `schemas/activation_receipt.schema.json` define the runtime evidence envelope.

A PASS receipt requires valid SHA-256 identities for the contract, backend artifact, checkpoint, input, and output. A REJECT receipt may contain null artifact fields when rejection occurred before those fields were structurally admitted; the raw attempted request remains bound by `intent_sha256` and the supplied authority material by `authority_payload_sha256`.

The current authority verifier exposes `ledger_event_type`, not a unique ledger-event identifier. Therefore `authority_event_id` is explicitly nullable. The runtime does not invent a ledger identity from another hash.

## Runtime-integrity tripwires

The in-process native seam now:
- resolves and pins the requested shared-library path
- fails closed when dynamic-loader influence variables such as `LD_PRELOAD`, `LD_LIBRARY_PATH`, or `LD_AUDIT` are present
- requests local/immediate symbol resolution where the platform exposes it
- on Linux, verifies that the target library is mapped from the expected path/device/inode
- rejects deleted target mappings
- rejects writable+executable mappings for the target library
- repeats the mapping check after execution
- retains file hashing before load, after load, and after execution

These checks do not prove arbitrary process-memory integrity, do not hash relocated executable pages, and cannot undo a preload/interposer that entered before the current process started. Full loader-environment sanitization requires a fresh isolated worker process. Dependency closure/RPATH/RUNPATH attestation is also not yet claimed.
