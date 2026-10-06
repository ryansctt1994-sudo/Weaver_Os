# Weaver OS

**Deterministic verification and replay substrate for bounded probabilistic cognition.**

Weaver OS is a compact verification spine for checking authority claims, replay protection, schema alignment, and release provenance. The repository is intentionally kept small: useful code, tests, schemas, and promotion rules stay; speculative or non-executable material belongs in external research notes until it has implementation evidence.

## Portfolio Status

See [`PORTFOLIO_STATUS.md`](PORTFOLIO_STATUS.md) for the canonical portfolio status and [`PORTFOLIO_REGISTRY.md`](PORTFOLIO_REGISTRY.md) for the complete repository/upstream provenance inventory.

## Core Thesis

Cognition may propose, but it cannot authorize itself. Weaver OS turns authority claims into signed, replay-checked, schema-validated artifacts so rejected or invalid claims cannot silently become trusted state.

## Current Scope

This repo currently contains:

| Module or directory | Purpose |
| --- | --- |
| `triadic_controls/` | Signature verification, replay cache, and authority schemas |
| `src/weaver_release_guard/` | Release provenance CLI, OIDC verification, and utilities |
| `canonical/` | Canonical serialization |
| `chronicle/` | Hash-chained event history |
| `chronicle-raft/` | Go HTTP attestation snippet |
| `compression/` | Residual monitoring |
| `kernel/` | Deterministic state reduction |
| `policy/` | Policy gate and signed-verifier adapter |
| `receipt/` | Receipt construction and verification |
| `weaver_auth/` | Identity resolution and bedrock admission/pathology checks |
| `witness_py/` | Attestation signing helper |
| `tools/` | Archive and ledger verification, verified witness runner, mutation checks, and MathOS benchmark |
| `demo/` | Demonstration inputs and execution scripts |
| `operator-kit/` | Operator runbook and receipt tooling |
| `schemas/` | Shared artifact schemas |
| `tests/` | Verification, policy, replay, and release tests |

Root scripts include `inject_ledger.py` and `verify_attestations.py`. Default
`pytest -q` also collects the admission and pathology tests in
`weaver_auth/bedrock/tests/`. These components have different validation scopes;
being listed here does not imply certification or deployment authority.

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

## Short witness demonstration

After installation, run:

```sh
python -m tools.reproduce_witness --operator YOUR_IDENTITY --output ../witness-result
```

This checks authorized acceptance, unauthorized rejection with unchanged state,
fresh-process replay, and tamper rejection. It preserves a timed outcome and raw
runner logs. See the [independent reproduction runbook](docs/releases/independent-reproduction.md)
for the sealed target, operator signing, and review procedure. The output directory
must be new. An author-side or CI run does not establish witness independence.

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
