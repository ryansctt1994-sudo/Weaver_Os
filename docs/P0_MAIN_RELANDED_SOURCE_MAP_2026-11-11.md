# P0 integration candidate — source and scope map

**Status:** DRAFT, LOCAL/CI CANDIDATE ONLY · E2/W0/O0_WITHHELD · PRODUCTION PROHIBITED  
**Base `main` commit:** `55bdfb9fce42065a0c97b3249e9887454b58a23b`  
**Base `main` tree:** `9413c5067731d4a75c35bb6aeacc4ae3502f94f6`  
**Common ancestor of `main` and PR #91:** `50ffc20917e4ca2748f3f647acaec23b3f724855`

## Source inventory

- **PR #91**, exact head `6515982c2c30cf57e74879d79f42d370f118f1e5` (tree `d8e8af0ad84f94a89b0a12806b04f294d693f573`): 34 Git blob objects with their original file modes copied onto the current `main` tree. This includes the source integration of #80/#83/#84 through #86, the adversarial verdict gate #87, #88's witness-policy HOLD packet, strict JSON intake from #90/#89, numeric-overflow rejection, corrected E3.5 classification, independent evidence-bundle checker, and exact-source rehearsal. The transfer is **not** a Git merge or independently authenticated reproduction.
- **PR #114**, exact head `3bdab26d021b66ab01a44af211c084424605698f` (tree `90900c1c0ed0a39000982ec91dd22377f297d35f`): overlay precisely `tools/verify_all.py` and `tests/test_verification_output_preflight.py`, retaining the dependency installer workflow's existing regular `install.log` exception.
- **Rehearsal workflow adjustment:** restrict the exact-head operator job to this candidate branch `integration/p0-main-reland-20261111-v1`, replacing the obsolete PR #91 branch selector. This is an integration-specific workflow change, **not** a source-identical copy of the original file.
- **This provenance document:** new integration note; documentation, not test evidence.

## Ancestry and conflict check

The GitHub compare API identifies the shared ancestor above and reports PR #91 `47 ahead / 37 behind` the inspected `main`. The 34 changed paths on the #91 side have **zero filename overlaps** with the 109 changed paths on the `main` side since the common ancestor. The two #114 changed paths are those documented in its exact stacked delta. The full integrated source is a **new** commit tree and must be separately validated.

PR #90 is **not** a commit ancestor of #91: its strict JSON component was integrated as file content. The original #90 intake test blob `40f1de47c59a54410f06561bb88a934a77c35eaa` is retained in #91. The final #91 verifier blob is newer than #90 because it also rejects exponent overflows such as `1e999`.

## Not imported

- PR #108 (`6324c16dbbb5783b895d25e118ce816c9026596b`) is an **independent** evidence-binding path/JSON hardening review; its already-existing `main` paths are untouched by this P0 candidate.
- PR #115 (`467186f51f997acc6d9ee038615e1f3f1bbd4a5a`) remains a separate review-ready CI pipeline patch and is **not merged** or silently included here.
- No historical manifest, authority ledger, published release, trustee policy, or independent witness custody is promoted.

## Acceptance gate before considering review promotion

1. Confirm this candidate source head, parent, Git tree and source-file inventory.
2. Inspect **fresh** workflow results for `CI`, `tests`, `Verification evidence`, `E3.5 hold`, `Hardware simulation`, `Witness TLA model`, `triadic-controls`, `Cross-host spine`, and **Exact-commit operator rehearsal**. A skipped job does not count as a PASS.
3. Review full logs and artifacts; run the aggregate verdict, JSON duplicate/NaN/overflow, manifest shadowing, tampered bundle, dirty tracked-source, and stale-output negative controls on this **exact** candidate.
4. Check integration of future #115 and #108 decisions with a new source HEAD and CI.
5. Require separate human authorization for any merge; an externally controlled witness and governance approval for any E/W/O elevation.

**No claim of independent reproducibility, hardware performance, physical-world correctness, deployment readiness, or authority promotion.**
