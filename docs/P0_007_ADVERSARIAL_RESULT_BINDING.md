# P0-007 — Bind adversarial PASS to actual rejection

**Classification:** maintained-source review candidate, dependent on P0-006.
**Base source:** P0-006 PR #86 commit
`36b49fa8cd324e49f968ab65db3b443b31d565c4`.
**Authorization:** E2 ceiling / W0 / O0 WITHHELD / PRODUCTION PROHIBITED.

## Confirmed false-positive path

The evidence producer previously accepted all six adversarial cases when
`status=PASS`, without checking each case's `observed_verdict`,
`exit_code`, and nonempty `failure_code`. The report schema also allowed
`status=PASS` with `observed_verdict=UNEXPECTED_PASS` or a zero exit code.
The read-only consumer checked hashes and cross-report agreement, but did not
reject the same contradictory *self-consistent* case records or a positive
baseline whose recorded exit code was nonzero.

Reproduced in GitHub-hosted Python 3.12 tests at test-only commit
`9673528657ce8663499c51c1d3817ac2e7d29e57`:
[RED workflow](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37881830619):
**7 failed, 201 passed**. Three producer tests plus three rehashed-bundle
consumer tests plus one positive-baseline exit-code test. Adversarial-case
bundle tests deliberately recompute the manifest SHA-256 and duplicate report
bytes to demonstrate that hash self-consistency alone does not establish
semantic consistency.

## Repair surface

- `tools/verify_all.py`: PASS requires each adversarial case to have
  `expected_verdict=REJECT`, `observed_verdict=REJECT`,
  `status=PASS`, a nonzero integer exit code, and a nonempty failure code.
- `schemas/verification_run.schema.json`: a PASS adversarial case must
  structurally bind the observed verdict and exit code to the expected
  rejection and carry a nonempty failure code.
- `tools/verify_evidence_bundle.py`: independently refuse positive baseline
  cases that lack a zero process exit code; report the exact failing schema
  location when a case is contradictory.
- Regression probes exercise all these failures against the real source
  and synthetic fully rehashed bundles.

The genuine adversarial corpus runner already computes its status using
rejected exit codes and expected error text. This patch defends the
*consumption and aggregation boundary* against contradictory reported
results; it does not assert that scripts were truly executed by a trusted
party or that the reported stderr actually came from a trusted process.

## Replay

```bash
python -m pytest -q tests/test_verification_report.py \
  tests/test_evidence_bundle_independent.py
python -m pytest -q
python -m ruff check .
python -m mypy .
```

Review GitHub-hosted CI at the **final patch head**, not earlier successes.
P0-006 and all other PRs remain untouched. No signed external witness,
source-policy attestation, deployment, or authority change is introduced.
