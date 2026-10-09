# P0-009 · Source-pinned PR #88 + PR #90 integration candidate

**Document class:** E1 engineering integration specification; not a test receipt.
**Standing:** E2 portfolio ceiling · W0 · O0 WITHHELD · PRODUCTION PROHIBITED.
**Promotion:** none. **Merge:** withheld. **Witness policy:** unresolved.

## Source precedence (review this before merging)

- Common integrated ancestor PR #86: `36b49fa8cd324e49f968ab65db3b443b31d565c4`.
- Base PR #88 exact head: `6748a3c76f960f5df119ce00295eab22b7bd3064`.
- Additional PR #90 exact head: `033d711560384e45beb67afb1a4023c191c2338e`.
- PR #88 is ten commits ahead of #86 and modifies fourteen files beyond the common ancestor.
- PR #90 is two commits ahead of #86 and modifies **only** `verify_attestations.py` and `tests/test_claim_e3_001_json_intake.py` beyond that ancestor.
- Base `verify_attestations.py` Git blob: `a235bc98c375209eafb73f6733bb03e32cf2d7b5`.
- PR #90 strict verifier Git blob: `f04143a78d6cd7898f484cfb3304b7e1007c486d`.
- PR #90 test Git blob: `40f1de47c59a54410f06561bb88a934a77c35eaa`.

The integration branch was created directly from the exact PR #88 head and overlays **only** those two original PR #90 files without rewriting any PR #88 verifier, manifest, adversarial, schema, receipt, or policy source. The accompanying tests run both policies in one interpreter. This is a deterministic file-level integration, not proof that original branches were merged through Git's merge algorithm.

## Required executable gates

```bash
python -m pytest -q tests/test_claim_e3_001_json_intake.py tests/test_p0_009_integration.py tests/test_verification_report.py tests/test_evidence_bundle_independent.py tests/test_witness_policy_freeze.py
python -m pytest -q
python -m tools.witness_policy_freeze
# MUST refuse (nonzero):
python -m tools.witness_policy_freeze --freeze
python verify_attestations.py --scope local-spine
# MUST withhold (nonzero):
python verify_attestations.py --scope e35
```

Hosted `tests`, `CI`, `verification evidence`, `E3.5 hold`, `cross-host spine`, `TLA`, and `triadic-controls` must be inspected at the **final head**. The verification-output checker must report `LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION`. Log counts, timestamps, command lines and exact result must be placed in an *external or later head-bound receipt*, not predicted here.

## False-green counterexamples and AURELIA reconciliation

- **H1 / false-green attribution:** `HashConsistentVerification != CorrectAdversarialVerdict`. PR #87 observed incorrect successful adversarial labels even after recomputing bundle hashes. The suite requires semantic rejection evidence rather than a digest-only conclusion.
- **H2 / nontransfer:** `GreenPR(A) + GreenPR(B) != GreenCombinedHead`. The combined head is its own source object and needs fresh CI.
- **H3 / partial source-lock:** an artifact SHA-256 alone does not authenticate source lineage. Public Evidence Gate v0.2 is a local byte-bound prototype, not a trusted release attestation.
- **H4 / faithful HOLD:** four declared witness policies remain visible. `tools/witness_policy_freeze.py --freeze` must refuse. Do not auto-select a policy based on passing CI.
- **H5:** AURELIA / LUX ORDO v3.0 F1–F9 freeze gate remains **NOT ADJUDICATED BY THIS PR**; this integration cannot substitute for its separate closure.
- **H6:** portfolio maturity categories are reviewer interpretations, not machine-verifiable evidence state.
- **H7:** any truncated handoff copy should be corrected at the publishing source, not interpreted as changed authority.
- Counterexample museum candidates: Chronicle, control plane, VTK, stale-pin public spine and P0-007 hash-consistent false-green. Previous cases are historical/reported unless their exact independent receipts are separately attached.

No fourth top-level root. MYTHOS · LOGOS · PRAXIS. Human judgment remains in authority.

## Required separate review

1. Verify this branch preserves all PR #88 changed files by Git blob SHA and restores the exact two PR #90 blobs.
2. Inspect source, tests and the native CI execution logs, including the deliberate nonzero witness-policy freeze and E3.5 refusal.
3. Human-review for semantic conflicts, then verify effective server-side branch/ruleset protection.
4. Resolve the competing witness identities **explicitly and externally** before any witness admission.
5. Freeze a release only after one accepted reviewed source, exact toolchain and dependency lock, negative controls, and reproducible command output.

**Initial outcome:** SOURCE-ASSEMBLED / VALIDATION-PENDING. This file must not be rewritten merely to make a review gate appear green.


## Discovered P0-009 false green (RED preserved)

At the initial combined source head `ea721ff1c9a7e93a337f405f27c0235d061c0ad3`, hosted run
[`37887781167`](https://github.com/ryansctt1994-sudo/Weaver_Os/actions/runs/37887781167)
completed SUCCESS even though `verify_attestations.py` terminated at import time:

```text
ModuleNotFoundError: No module named 'jsonschema'
EXPECTED_RED_E35_CONFIRMED
```

The original CI script accepted *any* code 1 as legitimate E3.5 refusal. This is a separate
false-green attribution defect: `NonzeroExit != ExpectedPolicyRefusal`.

**Repair:** the `e35-hold.yml` job installs the declared version-pinned verification
dependencies and executes `python -m tools.check_e35_withheld`. Its positive control
requires the actual local-spine verifier to succeed with all five digest/method PASS
markers. Its negative control requires E3.5 to exit 1 **with the exact reason and
`RESULT: E3.5_WITHHELD` marker**, and no traceback or unexpected stderr.
The machine-readable `e35-output.txt` stores both invoked commands, stdout,
stderr, exit codes, interpreter and source-head claim for later audit.

The pre-repair E3.5 workflow run is **INVALID AS GOVERNANCE-HOLD EVIDENCE**
regardless of its GitHub-green label. Neither that defect nor this patch changes
`W0`, `O0`, release identity, or independent verification.

**New acceptance rule:** the corrected workflow must pass on its new source head,
and the raw checker receipt must be examined before admitting a bounded E3.5 HOLD
observation. Do not infer correctness from a GitHub job status alone.
