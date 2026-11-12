# Release Readiness Checklist

This checklist defines the minimum receipts required before Weaver OS can be labeled as a release candidate.

Current posture: **DEVELOPMENT / VERIFICATION SPINE**. Release candidate: **NOT EARNED**. One required receipt is BLOCKED, and the production-blocking gaps below are open.

Do not mark this repository production-ready until every required receipt below is present and linked from the release notes.

## Reconciled against

- **Commit:** `main` at `c24f7cbadc3d1c9898cfaee6caf1b6b0590a8990` (merge of PR #119), reconciled 2026-11-12.
- **Raw receipts:** [`evidence/release-readiness/main-c24f7cb/`](../evidence/release-readiness/main-c24f7cb/) (`receipt.json` plus the raw outputs it hashes).
- **Trust scope:** E2 / W0 / O0_WITHHELD; production PROHIBITED. Every PASS below is bounded to the named commit, run, and host. "Session container" means a Claude session cloud container, a publisher-controlled host. Nothing here is independent reproduction or a signed attestation.

Every requirement carries exactly one status:

- **PASS:** the evidence named next to it exists at the commit above.
- **BLOCKED:** the evidence does not exist, and the reason is stated.
- **NOT RUN:** nobody has attempted it.

A missing receipt is never recorded as a pass.

## Required receipts

### 1. Local pytest receipt

Command:

```bash
python -m pip install -e ".[dev]"
pytest
```

| Required evidence | Status | Evidence |
| --- | --- | --- |
| Full pytest pass output | **PASS** (session container) | `772 passed`, exit 0: [`pytest.txt`](../evidence/release-readiness/main-c24f7cb/pytest.txt) |
| Python version used | **PASS** | Python 3.13.18. This is outside the CI matrix (3.10–3.12). Resolved packages: [`pip-freeze.txt`](../evidence/release-readiness/main-c24f7cb/pip-freeze.txt) |
| Commit SHA tested | **PASS** | `c24f7cb`, in a clean checkout; no tracked changes before or after |

Status: **PASS**, scoped to the session container. No receipt exists from an operator-owned machine. If "local" is meant to mean the operator's own host, this requirement is **NOT RUN** for that host.

### 2. GitHub Actions receipt

| Required evidence | Status | Evidence |
| --- | --- | --- |
| Successful `tests.yml` run on `main` | **PASS** | Run [43157872210](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/43157872210), push to `main`; each job checked out `c24f7cb` |
| Matrix success for Python 3.10, 3.11, and 3.12 | **PASS** | [3.10.22](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/43157872210/job/130981919296), [3.11.18](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/43157872210/job/130981919371), and [3.12.16](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/43157872210/job/130981919007): `772 passed` in each |
| Workflow URL or run ID | **PASS** | As above |

Status: **PASS**.

Other workflows on the same push:

- **Succeeded:** CI, Cross-host spine receipt, Exact-commit operator rehearsal, Hardware simulation, Witness TLA model, triadic-controls CI, and [Verification evidence](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/43157872347). In Verification evidence, `make verify` passed, and the bundle check reported `BUNDLE_BYTES_CONSISTENT` with assurance `LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION`.
- **Not triggered, as designed:** E3.5 hold gate (runs on pull requests and manual dispatch only), and gate1 and boundary-integrity-demo (both path-filtered).

### 3. Build receipt

Command:

```bash
python -m build
```

| Required evidence | Status | Evidence |
| --- | --- | --- |
| Successful wheel build | **PASS** | The CI build step succeeded on 3.10, 3.11, and 3.12 (run 43157872210), and in the session container |
| Successful sdist build | **PASS** | Same runs |
| Built artifact names | **PASS** | `weaver_os-0.5.0-py3-none-any.whl`, `weaver_os-0.5.0.tar.gz` |
| SHA-256 digests of retained artifacts | **BLOCKED** | No wheel or sdist built from `c24f7cb` was retained together with its digest. See below. |

Status: **BLOCKED**, on retained-artifact digests.

Why retained-artifact digests are blocked:

- **`tests.yml`** builds the wheel and sdist but neither hashes nor uploads them, so they are discarded with the runner.
- **Verification evidence** (run 43157872347) builds a wheel only, no sdist. `tools/verify_all.py` writes that wheel's digest into its report as `wheel_sha256`. The workflow retains `verification-output/` as artifact 13916054285, which holds the report but not the wheel. So a digest was kept for a wheel that was not. The artifact's storage host is outside this session's network allowlist, so that digest was not read or confirmed here.
- **Session-container builds** were hashed ([`build-digests.txt`](../evidence/release-readiness/main-c24f7cb/build-digests.txt)), but the artifacts were not retained; they existed only in an ephemeral container.

A digest identifies one specific artifact, and anyone holding that artifact can recompute it. What is missing is a retained artifact paired with its recorded digest. Uploading `dist/` together with its SHA-256 from CI would unblock this; that change is not made here.

Whether a rebuild from source reproduces a recorded digest is a separate question, tracked under [Reproducible builds](#reproducible-builds).

### 4. CLI smoke receipt

Commands:

```bash
weaver-release-guard --help
weaver-release-guard generate --help
weaver-release-guard verify --help
```

| Required evidence | Status | Evidence |
| --- | --- | --- |
| Successful output for all three commands | **PASS** | The CI step "Run CLI smoke checks" succeeded on 3.10, 3.11, and 3.12. In the session container, all three exited 0: [`cli-smoke.txt`](../evidence/release-readiness/main-c24f7cb/cli-smoke.txt) |

Status: **PASS**. These commands show only that the CLI loads and prints help. They do not exercise `generate` or `verify`.

## Tracked separately

### Reproducible builds

This is not a required receipt in this checklist. Status: **NOT ESTABLISHED**.

In the session container, two consecutive `python -m build` runs on clean `c24f7cb` produced different SHA-256 digests for both the wheel and the sdist. Member contents were identical (wheel 49 of 49 members, sdist 108 of 108); only member timestamps differed (6 wheel members, 27 sdist members). See [`build-digests.txt`](../evidence/release-readiness/main-c24f7cb/build-digests.txt).

So a rebuild from source does not reproduce a recorded digest, and nobody can confirm by rebuilding that a given artifact came from this commit. That is separate from checking an artifact you hold against its recorded digest, which non-reproducibility does not prevent. Pinning build timestamps, for example with `SOURCE_DATE_EPOCH`, is a candidate fix; it has not been tried.

## Remaining open gaps

This section is reconciled against the merged code at `c24f7cb`. It does not count a backlog item as complete because a PR exists. These gaps do not block local verification, but they block production readiness.

| # | Gap | State on `main` at `c24f7cb` |
| --- | --- | --- |
| 1 | `registry_sequence` rollback protection | **OPEN, narrowed.** PR #119 enforces it only when a caller supplies a `registry_sequence_store`. The first registry seen for an ID is trusted on first use. No non-test code constructs `CryptoVerifier`, so nothing in production uses it yet. Schema requirements are undecided (#121). See `docs/ENFORCED_VS_METADATA.md`, known gap #1. |
| 2 | `signing_domain` semantic allowlist | **OPEN.** Signed but not allowlisted on `main`. A candidate fix is in draft PR #122, unmerged. |
| 3 | `payload_schema_version` semantic allowlist | **OPEN.** Same as gap #2; draft PR #122. |
| 4 | Production-grade persistent replay cache with atomic multi-process `check_and_record` | **OPEN.** `SQLiteReplayCache` is tested with 32 threads against one cache object (`test_sqlite_cache_concurrent_check_and_record_is_atomic`). No test covers multiple processes or a crash. |
| 5 | Release-guard negative-path tests | **OPEN, wider than "expansion".** No test in the pytest paths imports `weaver_release_guard`. The only coverage is the `--help` smoke step. |
| 6 | Commit boundary atomic with veto and revocation | **OPEN.** C-GATE-001 in `governance/CONTRADICTIONS.yaml`. |
| 7 | `AuthorizationDecision` bound to the proposal it was issued for | **OPEN.** Recorded as an open limit in `governance/specs/WX-EXECUTION-GATE-1.md`; tracked in #120. |

## Status vocabulary

- **PASS / BLOCKED / NOT RUN:** status of a required receipt, defined above.
- **NOT ESTABLISHED:** a property that was checked and does not hold. Used for items tracked outside the required receipts.
- **IMPLEMENTED:** code or documentation exists in the repository.
- **TESTED:** local command output proves behavior at a specific commit.
- **CI PASSED:** GitHub Actions passed at a specific commit.
- **OPEN GAP:** known remaining architectural or test debt.
- **RELEASE CANDIDATE:** every required receipt is PASS, and no production-blocking gap remains.
