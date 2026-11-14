# Local test reproduction record, 2026-11-12

Scope: a single local re-run of the test suite and the verifier mutation check at two commits. It repeats what the hosted workflows already ran. It does not change any evidence class, witness level or authority state, and it does not promote anything.

Who ran it: an AI coding session working in the repository owner's cloud container. Same operator and same infrastructure as the code under test, so this is not an independent witness (W0 is unchanged).

## Environment

- Linux container, Python 3.13, pytest 8.4.2
- `python -m pip install -e ".[dev]"` (the same install step as `.github/workflows/tests.yml`)
- Each ref was run from a clean checkout of that ref

## Results

| Ref | Command | Result |
|---|---|---|
| `main` at `7f839ef` | `pytest -q` | 783 passed |
| PR #125 head `6ffeeda` | `pytest -q` | 800 passed, 1 xfailed |
| PR #125 head `6ffeeda` | `python -m tools.check_verifier_mutations` | 51 of 51 mutations detected, script exit code 0 |

The 800 figure belongs to the PR #125 head. `main` has 783 tests and no expected failure.

The 51 mutations include the three vertical-slice cases `vertical-signer-check-unwired`, `vertical-atomic-effect-unwired` and `vertical-owner-resource-write-skipped`. Each one is detected by at least one failing test.

The one expected failure is `test_v008_direct_sqlite_bypass_must_be_denied_by_os`. It is marked `xfail(strict=True)`, so it records that a same-UID process can still edit the SQLite file directly. If that bypass is ever closed without removing the marker, the suite fails.

## Not covered by this record

- GitHub Actions results. Only the commands above were re-run locally.
- Any OS-level isolation of the resource owner (V008 remains open).
- Any check by a party independent of the repository owner.
- Python 3.10 to 3.12, which is the hosted matrix in `.github/workflows/tests.yml`. Only 3.13 was run here.
