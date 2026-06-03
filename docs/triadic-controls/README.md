# triadic-controls

`triadic-controls` is an authority-decay and cryptographic authorization-control framework for high-stakes autonomous or semi-autonomous systems.

It is designed to integrate naturally with Weaver OS concepts: deterministic replay, rejected-authority proofs, cryptographic receipts, and constitutional execution boundaries.

## Current baseline

```text
Package: triadic-controls
Baseline: v0.3.1
Completed artifacts: TSC-001, TSC-001A, TSC-001B
Next target: v0.4.0 / TSC-001C
Status: pilot-ready for simulation, CI validation, research, and non-safety-critical integration
Production status: not safety-critical ready
```

## Core invariant

A system may be capable of acting, but it may only act inside valid, current, contestable authority.

## Completed artifacts

### TSC-001 — Trust Ledger and Authority Decay Controls

Defines authority levels, expiring authority tokens, refusal signals, deterministic downgrade rules, handoff shock, noncomputable flags, fallback hooks, and Trust Ledger requirements.

### TSC-001A — JSON Schemas + State Machine

Defines machine-readable schemas for authority tokens, refusal signals, ledger entries, noncomputable flags, and deterministic transition semantics suitable for CI validation.

### TSC-001B — Python Reference Implementation

Defines the v0.3.1 pilot reference implementation: authority resolver, schema-backed objects, hash-chained ledger, canonical JSON hashing, refusal caps, and deterministic downgrade handling.

## Next artifact

### TSC-001C — Cryptographic Authority & Refusal Verification

Adds Ed25519 verification, domain-separated signing objects, key registries, role policies, quorum independence, replay protection, and cryptographic verification results.

TSC-001C does not prove legitimacy. It proves cryptographic authorization claims.

## Corrected cryptographic boundary

Cryptography proves:

- which key signed a payload,
- which issuer claims that key,
- whether the key was active,
- whether the payload changed,
- whether the role was authorized,
- whether quorum independence was satisfied,
- whether replay protection passed.

Cryptography does not prove:

- the action was morally justified,
- the operator understood the request,
- the institution was legitimate,
- the authorization was free from dependency gravity or rubber-stamping.

## Safety warning

This framework is not ready for production safety-critical deployment until cryptographic verification, key management, external ledger witnessing, threat modeling, concurrency control, and domain-specific safety validation are complete.
