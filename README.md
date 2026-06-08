# Weaver OS

**Deterministic verification and replay substrate for bounded probabilistic cognition.**

Weaver OS is a compact verification spine for checking authority claims, replay protection, schema alignment, and release provenance. The repository is intentionally kept small: useful code, tests, schemas, and promotion rules stay; speculative or non-executable material belongs in external research notes until it has implementation evidence.

## Core Thesis

Cognition may propose, but it cannot authorize itself. Weaver OS turns authority claims into signed, replay-checked, schema-validated artifacts so rejected or invalid claims cannot silently become trusted state.

## Current Scope

This repo currently contains:

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
  provenance.py        # Release provenance generation and verification
  oidc.py              # Optional OIDC token verification
  utils.py             # Shared hashing, JSON, and encoding helpers

tests/
  triadic_controls/    # Crypto verifier and schema-alignment tests
```

## Repository Policy

```text
architecture != authority
specification != implementation
declared_success != replay_verified_success
capability != authorization
```

Promotion requires passing tests, reproducible commands, and explicit receipts. See [`docs/PROMOTION_RULES.md`](docs/PROMOTION_RULES.md).

## Install

```bash
python -m pip install -e ".[dev]"
```

## Run Tests

```bash
pytest -q
```

## Build

```bash
python -m build
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

This package verifies cryptographic authorization claims. It does not prove human legitimacy, moral legitimacy, operational safety, or production readiness. Those require higher-level governance, Chronicle/replay evidence, deployment policy, and independent receipts.

## Status

```text
MVP_VERIFICATION_SPINE
ARCHITECTURE_FROZEN
EVIDENCE_NOT_FROZEN
AUTHORITY_NOT_EARNED
```

Production deployment still requires persistent replay-cache storage with atomic multi-process semantics, operational key management, deployment-specific governance policy, and independent replay receipts.

## License

MIT
