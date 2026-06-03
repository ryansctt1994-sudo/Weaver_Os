# Weaver OS

**Deterministic verification and replay substrate for bounded probabilistic cognition.**

Weaver OS is a verifiable execution and release-governance substrate for bounded AI systems. Its current public spine focuses on cryptographic authority verification, replay protection, production schema alignment, and release provenance checks.

## Core Thesis

Cognition may propose, but it cannot authorize itself. Weaver OS turns authority claims into signed, replay-checked, schema-validated artifacts so rejected or invalid claims cannot silently become trusted state.

The current MVP supports:

- **Cryptographic authority verification** with domain-separated Ed25519 signatures.
- **Payload binding** through canonical JSON and SHA-256 payload hashes.
- **Replay protection** with nonce/scope/system-bound replay keys.
- **Key lifecycle enforcement** for active, revoked, expired, suspended, and rotated keys.
- **Separation-group quorum enforcement** for high-authority operations.
- **Production JSON Schema alignment** for issuer records, key registries, role policies, signature envelopes, and verification results.
- **Release provenance verification** through the `weaver-release-guard` CLI.

## Current Repository Layout

```text
triadic_controls/
  crypto/
    replay.py          # Replay-cache protocol and in-memory implementation
    verifier.py        # Authority/refusal signature verifier
  schemas/
    issuer_record.schema.json
    key_registry.schema.json
    role_policy.schema.json
    signature_envelope.schema.json
    verification_result.schema.json

src/weaver_release_guard/
  cli.py               # CLI entry point
  provenance.py        # Weaver release provenance generation/verification
  oidc.py              # Optional OIDC token verification
  utils.py             # Shared hashing, JSON, and encoding helpers

tests/
  triadic_controls/    # Crypto verifier and schema-alignment tests
```

## Install

```bash
python -m pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## CLI

Generate release provenance:

```bash
weaver-release-guard generate \
  --dist-dir dist \
  --manifest manifest.json \
  --slsa provenance.json \
  --out weaver_provenance.json \
  --version 0.5.0 \
  --build-id "$BUILD_ID" \
  --policy-version v0.5.1 \
  --lease-id "$LEASE_ID" \
  --authority-level 3
```

Verify release provenance:

```bash
weaver-release-guard verify \
  dist/example.whl \
  manifest.json \
  weaver_provenance.json \
  --slsa provenance.json
```

## Security Boundary

This package verifies cryptographic authorization claims. It does not prove human legitimacy, moral legitimacy, or operational safety. Those must be enforced by higher-level governance, Chronicle/replay evidence, and deployment-specific policy.

## Status

MVP / verification spine. Suitable for local development, CI, and protocol hardening. Production deployment still requires persistent replay-cache storage with atomic multi-process semantics, operational key management, and deployment-specific governance policy.

## License

MIT
