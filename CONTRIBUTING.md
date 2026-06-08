# Contributing

Weaver OS is intentionally maintained as a compact verification spine.

## Contribution Standard

Useful contributions should improve one of these areas:

- cryptographic verification,
- replay protection,
- schema validation,
- release provenance,
- tests,
- documentation that explains real implemented behavior.

Avoid adding speculative modules, broad architecture dumps, or untested systems.

## Local Setup

```bash
python -m pip install -e ".[dev]"
pytest -q
```

## Pull Request Requirements

Each PR should include:

1. a clear summary,
2. tests for changed behavior,
3. evidence that tests pass,
4. no authority or production-readiness claims without receipts.

## Commit Style

Use direct, action-oriented commits:

```text
Add replay-cache eviction test
Fix signature envelope validation
Document release provenance boundary
```

## Authority Boundary

```text
specification != implementation
declared_success != replay_verified_success
capability != authorization
```
