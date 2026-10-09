# P0-005 — Portfolio PR integration and assurance preflight

**Classification:** draft research and review tooling. **Authority:** NONE.
**Portfolio ceiling:** E2. **Witness:** W0. **Operational:** O0 WITHHELD.
**Production:** PROHIBITED.

## Context and scope

This bounded cross-repository pass reconciles *GitHub source and pull request
metadata* with the historic portfolio context found in Drive. It does **not**
treat Drive narratives or Dropbox filenames as current executable code.

Portfolio top-level naming remains **MYTHOS · LOGOS · PRAXIS**; historic
"Weaver", "Academy", "Nexus", "Forge", "MedBio", and "Venture" are subordinate
programs/roles in historical records, not six additional peer roots. The
historical [Portfolio Status — 2026-10-07](https://docs.google.com/document/d/1P2f0zvK6Kohg4gZ8gcyUGh9vyF31bGS9v4L9TgoV79E/edit)
describes a six-system control plane and an *E0 reconstructed status*, not a
validated present-day registry or an independent evidence upgrade.

The snapshot at
`docs/maintenance/P0_005_REVIEW_SNAPSHOT_2026-10-09.json` records **six
selected open PRs in three maintained repositories** as observed through the
GitHub connector on 2026-10-09. It is not a complete account inventory and is
not auto-refreshed. Source fields distinguish observation from authorization.

## Observed overlap and enforcement uncertainty

1. `Weaver_Os` [PR #80](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/80)
   and [PR #83](https://github.com/ryansctt1994-sudo/Weaver_Os/pull/83)
   both change `tools/verify_all.py`. Their *individual* tests cannot show
   that both changes work together or whether Git would merge cleanly.
   Rebase / integrate only with an explicit combined diff and fresh CI.
2. `Weaver_Os` PR #82 (action boundaries) and PR #84 (read-only evidence
   verifier) have no observed changed-file overlap with #80 or #83, but
   API-level or semantic dependencies remain possible. Absence of overlapping
   paths is **not** evidence of runtime compatibility.
3. `Lumen` [PR #4](https://github.com/ryansctt1994-sudo/Lumen/pull/4)
   and `cathedral-verified` [PR #9](https://github.com/ryansctt1994-sudo/cathedral-verified/pull/9)
   are unmerged. Their positive local/CI results do not authorize production.
4. All three selected repository `main` branches returned
   `protected=false` through the branch API, and **zero repository-level
   rulesets** through the repository rulesets API at the time sampled.
   Organization-wide rulesets, administrator bypass behavior, and all other
   effective enforcement were **not inspected**; record this as
   `EFFECTIVE_RULESETS_UNVERIFIED`, not a definitive absence of all rules.
5. Dropbox search found historical Weaver ZIPs, but their **contents were not
   byte-retrieved or verified in this pass**. They are not code dependencies
   and cannot silently become canonical.

## Run

This program deliberately accepts a *supplied pinned observation*, not live
GitHub state:

```bash
python -m tools.portfolio_pr_gate \
    --snapshot docs/maintenance/P0_005_REVIEW_SNAPSHOT_2026-10-09.json
```

Returns machine-readable `HOLD` (advisory execution exits 0). For a caller
that wants the presence of a HOLD to fail a pipeline:

```bash
python -m tools.portfolio_pr_gate \
    --snapshot docs/maintenance/P0_005_REVIEW_SNAPSHOT_2026-10-09.json \
    --fail-on-hold
```

The strict mode exits **1** for HOLD and **2** for malformed input. Without
any recorded concerns, output is `REVIEW_REQUIRED`, **never** `PASS`,
`MERGEABLE`, `E4`, or `AUTHORIZED`. It cannot merge branches.

## Mechanical guarantees and negative controls

- Source observations require explicit schema, date and provenance label.
- Repository and pull request identities must be unique and structurally valid;
  source/base hashes are exact 40-character lowercase Git SHAs.
- Reject duplicate JSON keys, nonfinite constants, duplicate paths, path
  traversal, incomplete or contradictory statuses, and changed-file omissions.
- Consider only selected open, unmerged review PRs for file overlaps.
- Flag base drift relative to the *sampled* main SHA, draft status, and
  branch/ruleset enforcement not established in this limited snapshot.
- Refuse to equate path overlap with a proven textual merge conflict.
- Refuse to declare a clean portfolio or authority elevation when no
  overlapping paths are detected.

Tests exercise actual selected snapshot fields and mutation controls. Their
passing result validates the checker on its input, not truth or freshness of
the recorded GitHub state.

## Integration order (requires human review)

1. Pick *one* exact first independent-witness release and cold-test its
   instructions; the historical target drift between CALL-004,
   Kernel_final.lean, and WN-RECEIPT-CORE-1.0 must not be silently resolved by
   this script.
2. Freeze candidate SHA(s) and the relevant source-diff review before merge.
3. For `Weaver_Os` #80/#83, construct a reviewed combined candidate after
   confirming each original patch; then run the full native CI suite with
   all dependent branches or rebased changes and inspect failed/poisoned
   controls.
4. Obtain proof of effective branch protection, PR-only enforcement, and
   required status checks from GitHub administrators. CODEOWNERS alone is
   advisory until enforced by review rules.
5. Independently reproduce *one* release on a non-origin controlled environment
   with authenticated witness identity and a signed PASS/FAIL/INDETERMINATE
   receipt. A provider-passing CI job is not the independent witness.

Relevant external *design references*:
[SLSA v1.2 Verification Summary](https://slsa.dev/spec/v1.2/verification_summary)
separates policy identity from verified artifacts;
[in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md)
binds explicitly named subjects to digests. P0-005 is **not** an in-toto
attestation, supply-chain certification, or trusted release gate.

No production, authority, witness, or registry promotions are inferred from
this work.

**E2 / W0 / O0 WITHHELD / PRODUCTION PROHIBITED.**
