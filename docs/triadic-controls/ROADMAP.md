# triadic-controls Roadmap

Status: v0.5.1 hardening baseline.

This roadmap tracks the transition from a cryptographic verification library into a full execution-boundary framework for Weaver OS.

## Current baseline — v0.5.1

The current package provides:

- schema validation boundary,
- root-authenticated key registries,
- registry freshness enforcement,
- payload hash binding,
- replay-domain time-window enforcement,
- issuer key lifecycle enforcement,
- cryptographic algorithm and encoding strictness,
- persistent SQLite replay protection,
- Ed25519 signature verification,
- role authorization,
- separation-group quorum checks,
- pytest coverage for cryptographic, schema, registry-root, replay, SQLite durability, and SQLite concurrency paths.

The system proves cryptographic authorization claims. It does not prove human legitimacy.

## v0.6.0 — Authority Lease and TOCTOU Execution Gate

Goal: move from point-in-time verification to bounded execution authority.

Planned work:

- Add `triadic_controls.execution` package.
- Add `AuthorityLease` dataclass.
- Add lease creation from successful `VerificationResult`.
- Add pre-action check.
- Add midpoint checkpoint revalidation.
- Add pre-commit revalidation.
- Add safe-abort result for expired or downgraded authority.
- Add tests for long-running operation windows and irreversible commit gates.

Core invariant:

```text
verify -> reserve authority window -> execute -> revalidate before irreversible commit -> commit or safe-abort
```

## v0.7.0 — Trust Ledger v2

Goal: make verifier decisions and execution gates auditable.

Planned work:

- Add `triadic_controls.ledger` package.
- Add append-only JSONL ledger writer.
- Add canonical ledger entry hashing.
- Add hash-chain integrity verification.
- Add events for root registry validation, signature validation, replay detection, quorum failure, authority lease creation, revalidation failure, and safe abort.
- Add tests for tamper detection and chain validation.

Future hardening may include WORM storage, transparency logs, distributed witnesses, regulator-held checkpoints, or HSM-sealed checkpoint hashes.

## v0.8.0 — Scope Enforcement and Refusal Parity

Goal: ensure valid keys can act only inside their authorized operational scope.

Planned work:

- Enforce `RolePolicy.allowed_scopes.systems` against `replay_domain.system_id`.
- Enforce allowed regions and tasks against the inner payload scope.
- Enforce `max_authority_duration_sec` against replay-domain duration.
- Bind `scope_hash` to canonical payload scope material.
- Add full `REFUSAL_SIGNAL` test vectors.
- Add refusal cap semantics and refusal ledger events.
- Add invalid refusal flood anomaly handling design notes.

## v0.9.0 — Registry Lifecycle, Rotation, and Revocation

Goal: make registry evolution and key lifecycle state explicit and rollback-resistant.

Planned work:

- Enforce monotonic `registry_sequence` where previous registry state is available.
- Define `ROTATED` key semantics.
- Define `SUSPENDED` key semantics.
- Enforce revocation effective time.
- Validate `rotated_to_key_id` chains.
- Add rollback detection tests.
- Add registry lifecycle tests for active, expired, revoked, rotated, and suspended keys.

## v1.0.0 — Mandatory Secure Mode

Goal: remove transitional optional trust boundaries.

Planned work:

- Require schemas by default.
- Require `inner_payload` by default.
- Require `root_public_key_b64url` by default.
- Require signed registry by default.
- Require persistent or externally atomic replay cache for production mode.
- Reject floating signature verification.
- Publish final API compatibility contract.

## Non-goals

The framework does not prove moral legitimacy, democratic legitimacy, operator understanding, or institutional accountability. Those remain governance-layer responsibilities.
