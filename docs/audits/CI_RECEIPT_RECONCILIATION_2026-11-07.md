# Weaver OS — CI receipt reconciliation candidate (2026-11-07)

**Classification:** read-only GitHub evidence review; candidate documentation only. **No evidence-level, witness-level, authority, or release promotion.**

## Source pin

- Repository: `ryansctt1994-sudo/Weaver_Os`
- Audited `main` SHA: `55bdfb9fce42065a0c97b3249e9887454b58a23b`
- Scope: GitHub workflow run/job metadata and repository files. This record does **not** constitute a fresh clean-room reproduction, artifact-byte verification, or independent witness attestation.

## Observed successful workflows at pinned SHA

| Workflow | Run ID | Result | Coverage inspected |
| --- | --- | --- | --- |
| CI | [42401067651](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067651) | SUCCESS | Python 3.10 and 3.11; lint, trust-domain checks, verified-snapshot witness command, mypy, pytest, verifier mutations, package build |
| tests | [42401067728](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067728) | SUCCESS | Python 3.10, 3.11, 3.12; pytest, wheel/sdist build, CLI smoke checks |
| Verification evidence | [42401067766](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067766) | SUCCESS | Workflow conclusion only; job-level evidence not inspected in this review |
| Cross-host spine receipt | [42401067762](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067762) | SUCCESS | Workflow conclusion only |
| triadic-controls CI | [42401067746](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067746) | SUCCESS | Workflow conclusion only |
| Hardware simulation | [42401067693](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067693) | SUCCESS | Simulation workflow only; no physical hardware claim |
| Witness TLA model | [42401067673](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/42401067673) | SUCCESS | Bounded model workflow only; no full-system proof claim |

Seven listed runs for the pinned SHA were completed successfully. This does not establish that every workflow is configured to run on every push; in particular `e35-hold.yml` uses pull-request and manual triggers.

## Reconciliation against docs/RELEASE_READINESS.md

The existing release checklist still says PENDING for four receipt families. These are *candidate links* to reconcile, not unilateral checklist closure:

1. **Local pytest receipt:** NOT SATISFIED by hosted CI. Need local full stdout/stderr, interpreter version, environment and pinned SHA.
2. **GitHub Actions receipt:** The `tests` workflow has successful 3.10/3.11/3.12 jobs at the pinned SHA; the `ci` workflow itself has only 3.10/3.11. Confirm whether the checklist's `tests.yml` wording is satisfied by the three-job `tests` workflow and attach retained logs/artifact metadata before updating status.
3. **Build receipt:** Successful build steps exist in both workflows. Exact wheel/sdist filenames and independently recomputed SHA-256 hashes are NOT recorded in this review.
4. **CLI smoke receipt:** Successful CLI smoke step in the `tests` workflow; raw command output was NOT examined in this review.

## Current governing boundaries

Per `governance/decisions/GD-0005.md`, Step 7 is implemented using a simulated witness; `C-CUSTODY-001` remains OPEN, independent witness W0, evidence R2[self], authority O0/NONE, and E3.5 HOLD. `C-GATE-001` and other listed contradictions remain open. Neither green CI nor this note closes them.

## Next falsifiable actions

- Download and verify exact CI artifacts and job logs for the pinned SHA; preserve their hashes and toolchain versions.
- Run an independent checkout at the pinned SHA, collect full pytest denominator and mutation results (selected/executed/detected/survived/skipped/errored), and retain raw stdout/stderr and exit codes.
- Verify the release guard's rollback and semantic-allowlist negative cases and persistent replay-cache multi-process atomicity before claiming production readiness.
- Secure a separately controlled witness and rotation procedure; run a second-party reproduction before reconsidering C-CUSTODY-001.
- Preserve the E3.5 hold and all open contradictions until explicit adjudication.

**Disposition:** CI_PASS_OBSERVED · RELEASE_RECEIPTS_PARTIALLY_SUPPORTED · INDEPENDENCE_NOT_ESTABLISHED · NO_PROMOTION · NO_MERGE.
