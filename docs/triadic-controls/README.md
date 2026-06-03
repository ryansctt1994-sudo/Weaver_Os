# triadic-controls

`triadic-controls` is an authority-decay and cryptographic authorization-control framework for high-stakes autonomous or semi-autonomous systems.

It is designed to integrate naturally with Weaver OS concepts: deterministic replay, rejected-authority proofs, cryptographic receipts, and constitutional execution boundaries.

## Current baseline

```text
Package: triadic-controls
Baseline: v0.5.0
Completed artifacts: TSC-001, TSC-001A, TSC-001B, TSC-001C
Status: persistent, root-trusted cryptographic baseline
Production status: structurally sound for local deployment pilots; not yet safety-critical certified
```

## Core invariant

A system may be capable of acting, but it may only act inside valid, current, contestable authority.

## Verification spine

The v0.5.0 verifier executes authority validation through a fail-closed gate sequence:

```text
0. Schema validation boundary
1. Root registry signature verification
2. Registry freshness check
3. Payload hash binding
4. Replay-domain time-window enforcement
5. Issuer key lifecycle enforcement
6. Persistent replay check-and-record
7. Ed25519 signature verification
8. Role authorization
9. Separation-group quorum
```

## Completed artifacts

### TSC-001 — Trust Ledger and Authority Decay Controls

Defines authority levels, expiring authority tokens, refusal signals, deterministic downgrade rules, handoff shock, noncomputable flags, fallback hooks, and Trust Ledger requirements.

### TSC-001A — JSON Schemas + State Machine

Defines machine-readable schemas for authority tokens, refusal signals, ledger entries, noncomputable flags, and deterministic transition semantics suitable for CI validation.

### TSC-001B — Python Reference Implementation

Defines the v0.3.1 pilot reference implementation: authority resolver, schema-backed objects, hash-chained ledger, canonical JSON hashing, refusal caps, and deterministic downgrade handling.

### TSC-001C — Cryptographic Authority & Refusal Verification

Adds Ed25519 verification, domain-separated signing objects, key registries, role policies, quorum independence, replay protection, cryptographic verification results, schema validation, payload hash binding, registry freshness, issuer key lifecycle enforcement, persistent SQLite replay protection, and offline-root registry signature verification.

TSC-001C does not prove legitimacy. It proves cryptographic authorization claims.

## v0.5.0 additions

### SQLiteReplayCache

`SQLiteReplayCache` provides persistent replay protection using SQLite primary-key uniqueness and `INSERT ... ON CONFLICT DO NOTHING` semantics. It enables WAL mode, configures a busy timeout, and uses a fresh connection per operation to avoid Python thread-sharing hazards.

This replaces the in-memory pilot replay boundary for production-like deployments where replay state must survive process restarts.

### Root registry signature verification

`CryptoVerifier` can now be constructed with a pinned offline root public key:

```python
CryptoVerifier(
    key_registry=registry,
    replay_cache=cache,
    schemas=schemas,
    root_public_key_b64url=root_public_key,
)
```

When supplied, the verifier removes `registry_signature`, canonicalizes the remaining registry, and verifies the signature against the root key before issuer or role indexing. If this fails, construction halts.

## Corrected cryptographic boundary

Cryptography proves:

- which key signed a payload,
- which issuer claims that key,
- whether the key was active,
- whether the payload changed,
- whether the key registry was signed by the pinned root,
- whether registry and replay windows were current,
- whether the role was authorized,
- whether quorum independence was satisfied,
- whether replay protection passed.

Cryptography does not prove:

- the action was morally justified,
- the operator understood the request,
- the institution was legitimate,
- the offline root key was governed well,
- the authorization was free from dependency gravity or rubber-stamping.

## Safety warning

The v0.5.0 baseline is structurally hardened for local integration pilots, but safety-critical deployment still requires domain-specific threat modeling, secure offline key-management procedures, external ledger witnessing, operational runbooks, failure-mode analysis, and independent adversarial review.
