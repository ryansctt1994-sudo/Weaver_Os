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
