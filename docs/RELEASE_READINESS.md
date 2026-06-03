# Release Readiness Checklist

This checklist defines the minimum receipts required before Weaver OS can be labeled as a release candidate.

Current posture: **DEVELOPMENT / VERIFICATION SPINE**.

Do not mark this repository production-ready until every required receipt below is present and linked from the release notes.

## Required receipts

### 1. Local pytest receipt

Command:

```bash
python -m pip install -e ".[dev]"
pytest
```

Required evidence:

- Full pytest pass output.
- Python version used.
- Commit SHA tested.

Status: **PENDING**

### 2. GitHub Actions receipt

Required evidence:

- Successful `tests.yml` run on `main`.
- Matrix success for Python 3.10, 3.11, and 3.12.
- Workflow URL or run ID.

Status: **PENDING**

### 3. Build receipt

Command:

```bash
python -m build
```

Required evidence:

- Successful wheel build.
- Successful sdist build.
- Built artifact names and SHA-256 digests.

Status: **PENDING**

### 4. CLI smoke receipt

Commands:

```bash
weaver-release-guard --help
weaver-release-guard generate --help
weaver-release-guard verify --help
```

Required evidence:

- Successful command output for all three commands.

Status: **PENDING**

## Remaining open gaps

These gaps do not block local verification, but they block production readiness.

1. `registry_sequence` rollback protection.
2. `signing_domain` semantic allowlist.
3. `payload_schema_version` semantic allowlist.
4. Production-grade persistent replay cache with atomic multi-process `check_and_record` semantics.
5. Release-guard negative-path test expansion.

## Status vocabulary

- **IMPLEMENTED**: Code or documentation exists in the repository.
- **TESTED**: Local command output proves behavior at a specific commit.
- **CI PASSED**: GitHub Actions passed at a specific commit.
- **OPEN GAP**: Known remaining architectural or test debt.
- **RELEASE CANDIDATE**: All required receipts exist, and no production-blocking gaps remain.
