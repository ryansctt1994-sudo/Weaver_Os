# WC-4R-002 — Lumen Receipt & Chronicle Reproduction

**Observation:** 2026-11-13  
**Status:** OWNER_CI / INCOMPLETE · research-only · no merge · no production authority  
**Canonical candidate family:** `RECEIPT-LEDGER` (one of 18; not two families).

## Pinned provenance

- Donor repository: `ryansctt1994-sudo/Lumen` (Apache-2.0).
- Original code on `main`: `4a3240c4f47ca0e5cd9fc7423298c3b3c00db3bf`.
- Existing combined candidate repair: `7deeca5491153ffcbb6f2c815311fb5eefd7ce35`.
- Proposed repair integration: [Lumen PR #7](https://github.com/ryansctt1994-sudo/Lumen/pull/7), combining source PRs #4 and #5.
- New independent workflow definition for **owner-controlled** CI: [draft Lumen PR #8](https://github.com/ryansctt1994-sudo/Lumen/pull/8).
- Fresh exact-commit CI: [run 43528808402](https://github.com/ryansctt1994-sudo/Lumen/actions/runs/43528808402) — **SUCCESS** on workflow-only commit `517ce9c80e9c2629795cfdbe9755a08b948426c1`.
- Workflow artifact: `wc-4r-002-lumen-replay`, GitHub-reported SHA-256 digest `4a537a7424af3e07cde9fb2ddb6fd247ac667d69cd33272e903ea1fd3a250f86` (artifact downloadable through GitHub Actions; durability/independent custody pending).

## Fresh controls (all same regression bytes across BASE/FIX)

| Defect | Baseline at original commit | Candidate repair at exact integrated commit |
| --- | --- | --- |
| `LUMEN-CHRONICLE-RESUME-001` | Expected FAIL, including `test_prior_entry_tamper_denied_at_construction` | Chronicle integrity regression module PASS |
| `LUMEN-RECEIPT-BIND-001` | Expected FAIL, including `test_claim_substitution_is_refused` | Receipt binding and SQLite single-writer regression modules PASS |

Integration-specific evidence on the fixed code: `tests/test_integrated_evidence_boundaries.py` PASS and the entire `tests/` suite PASS. The workflow checks the original and repaired code SHA pins, byte-identical overlaid tests, tests' original git blob identifiers, and source file manifests unchanged before/after tests.

Each of the two separately bounded suites generates one raw baseline FAIL and one raw repair PASS: **four additional run-level ledger events**, **two linked repair passes**. These are *not* four test cases, four independent witnesses, or two new repository owners.

## Aggregate v0.2 ledger (including AL-SNAPSHOT-001)

- 18 candidate families, **2 freshly exercised families**, **16 not run**.
- **6** fresh run-level attempts: **3 FAIL**, **3 PASS**.
- **3** explicitly linked passing repairs, with **3** defects stopping at `REGRESSION_PASS`.
- **0** independently reviewed defects; **0** closed defects; **0** admitted witnesses.
- All fresh evidence `OWNER_CI / INCOMPLETE` pending independent byte-level inspection and durable custody.

The stored events use `source_sha` as the original code revision and `target_sha` as the exact code revision under test, allowing a repaired PASS to link to its original failure. `repair_of` is not proof of universal defect closure.

## Residual risks and scope

- The original Lumen fix PRs remain unmerged. No implementation files or default branches were altered by this run.
- These controls demonstrate the selected behavior of the proposed integrated revision, **not** externally authenticated receipts, signed witness, WORM durability, or protected execution.
- The separate `AUTH-REPLAY` catalog family remains `NOT_RUN`: a claim-binding test must not be relabeled as a capability-replay test.
- The rest of the ledger's security claims remain bounded by its internal hash links. An external anchor and independent replay are still required before a higher assurance classification.
- Retention of GitHub Actions artifacts is limited; the recorded digest is **not** itself independent artifact custody.

**Current authority:** O0 WITHHELD · **production:** PROHIBITED · portfolio evidence ceiling unchanged.
