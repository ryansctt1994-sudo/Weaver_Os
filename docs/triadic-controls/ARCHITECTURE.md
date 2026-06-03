# triadic-controls Architectural Layout

Status: v0.3.1 baseline accepted; v0.4.0 cryptographic verification target.

This document captures the corrected final architecture for `triadic-controls`, aligned with Weaver OS as a deterministic verification and replay substrate for bounded authority claims.

## Core invariant

A system may be capable of acting, but it may only act inside valid, current, contestable authority.

## Corrected cryptographic invariant

Cryptography does not prove human legitimacy. Cryptography proves that a specific key signed a specific canonical payload in a specific protocol context at a specific time.

Legitimacy remains a governance-layer responsibility.

## Layer 0 — Governance Layer

This layer remains outside the cryptographic boundary. It answers who should be allowed to authorize, who issued keys, who reviews abuse, and who is accountable when a technically valid authorization is morally or institutionally wrong.

The Trust Ledger records two forms of truth:

- Cryptographic truth: `key_id K signed payload P with signature S`.
- Operational truth: `issuer_id I claimed possession of K under role R at time T`.

It does not prove that the action was morally justified, democratically legitimate, or fully understood by a human operator.

## Layer 1 — Authority Control Layer

Authority levels:

```text
Level 5 — Full autonomy
Level 4 — Bounded autonomy
Level 3 — Supervised autonomy
Level 2 — Advisory only
Level 1 — Safe hold
Level 0 — Quarantine / revocation
```

Authority tokens may grant only Levels 1–5. Level 0 is not an authority grant. Level 0 is a revocation/quarantine state entered through external refusal, quarantine trigger, safety interlock, or verified constraint violation.

The resolver applies caps from valid token level, requested level, refusal signals, token expiry, handoff shock, cross-modal disagreement, calibration error, subsystem dissent, noncomputable flags, fallback unavailability, dependency gravity, and quarantine triggers.

## Layer 2 — Cryptographic Verification Layer

TSC-001C introduces:

```text
IssuerRecord
RolePolicy
KeyRegistry
SignatureEnvelope
SigningObject
ReplayCache
CryptoVerifier
VerificationResult
```

No authority grant or refusal cap is valid unless the system can prove which key signed it, which issuer claims that key, whether that key was active at signing time, whether the issuer role authorized the requested action, whether the payload was unaltered, whether quorum independence was satisfied, and whether the token or refusal signal is fresh and non-replayed.

This still does not prove moral legitimacy.

## Layer 3 — Trust Ledger Layer

The Trust Ledger is append-only and hash-chained. It records authority changes, token validation events, refusal validation events, signature failures, quorum failures, replay detections, key lifecycle events, handoffs, dissent, fallback tests, noncomputable flags, TOCTOU revalidation failures, and authority-window reservations.

Every cryptographic authority event should log both `issuer_id` and `key_id`.

The ledger is evidence, not absolution. v0.3.1 is tamper-evident, not tamper-proof. Future hardening should include WORM storage, transparency logs, distributed witness signatures, regulator-held checkpoint hashes, or HSM-sealed checkpoints.

## Layer 4 — Execution Gate Layer

The old model `verify once -> execute` is insufficient.

Corrected TOCTOU model:

```text
Verify
Reserve authority window
Execute
Revalidate before irreversible commit
Commit or safe-abort
```

Authority must not outlive its window. Long-running operations require checkpoint revalidation. Irreversible actions require immediate pre-commit revalidation.

## Layer 5 — Monitoring and Governance Feedback Layer

Cryptographically valid authorization can still be governance failure. A human may rubber-stamp every Level 4/5 request using a valid key. The ledger will show perfect cryptographic authorization, but governance has failed.

Monitoring controls should include approval-rate anomaly detection, repeated high-authority approval detection, operator fatigue indicators, challenge prompts, dual-channel approval, randomized review, dependency gravity alerts, and fallback drills.

## Canonicalization decision

Use RFC 8785 JSON Canonicalization Scheme as the baseline, with Triadic restrictions:

- No floats in authority-bearing payloads.
- No NaN, Infinity, or -Infinity.
- No `additionalProperties` in authority-bearing schemas.
- No ambiguous timestamps.
- No mixed public-key encodings.
- No signing of raw payload hashes alone.

The signing flow is:

```text
validate schema
reject unsupported numeric/value forms
canonicalize payload with RFC 8785
sha256 canonical payload
construct domain-separated SigningObject
canonicalize SigningObject with RFC 8785
sign SigningObject bytes with Ed25519
```

## Correct final system claim

Do not say: TSC-001C proves authority.

Say: TSC-001C proves cryptographic authorization claims.

Do not say: The Trust Ledger records who acted.

Say: The Trust Ledger records which issuer and key produced the authorization evidence used by the system.

Final architecture statement:

```text
TSC-001B establishes deterministic authority decay.
TSC-001C establishes cryptographic authenticity of authority claims.
Neither establishes human legitimacy.
Legitimacy remains a governance-layer responsibility.
```
