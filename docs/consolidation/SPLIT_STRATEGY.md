# WEAVER-CONSOLIDATION-SPLIT-001 — Controlled decomposition of draft #135

**Review-only. No merge, execution activation, evidence promotion, or production use.**

## Immutable input identities
- Canonical merged baseline: `main` at `7f839efad8c273b979678b0f94e5b1175136b0ab`.
- Existing owner/nesting dependency: draft #134 at `de15972b4fc29ec0a21f521ccf641946270ffcbf`.
- Previously tested combined reference: draft #135 at `f65fa54c56341a8d5508af728fc773055afa1cd2` (six hosted workflows green on that head).
- Source from draft #131 (ZOREL/Delta) remains separate and review-only. Do not relabel advisory status as owner authorization.

## Independent candidate slices (all based on #134)

| Slice | Branch | Scope | Runtime authority |
| --- | --- | --- | --- |
| A | `review/split-forge-custody-20261112` | Forge templates and donor MIT notices | None |
| B | `review/split-claim-audit-20261112` | Claim-audit tooling, contract tests and legacy report compatibility | None |
| C | `review/split-findings-20261112` | Finding confirmation and type-aware tests | None |
| D | `review/split-offline-proof-20261112` | Read-only offline publication verifier, fixtures and installed-wheel check | None |
| E | `review/split-arty-simulation-20261112` | Arty wrapper, simulations, physical test packet (manual only) | None |

The combined #135 branch remains a **read-only integration reference**, not the merge unit. The source manifest of 49 assets and eight donor archives remains intact there. Split candidates contain their own `docs/consolidation/slices/*.md` provenance. After separately validating and accepting selected slices, regenerate a fresh combined manifest against the exact accepted source. Do not claim the #135 green run transfers to an extracted branch.

## Dependency and disposition rules

1. All slices take **the same pinned #134 base**. They have no dependency on other split slices, though #134 itself remains unmerged and blocked by V008 HOLD. A future decision may retarget each slice to an accepted base; retargeting requires fresh CI.
2. ZOREL proposal bridge belongs in #130 and adversarial extension #131. Import neither as part of a tooling slice. The #135 combined testing is corroboration, not an independent release.
3. Keep the protected owner, `weaver_runtime.gate`, `ReceiptLedger`, signed grant and WX-CJSON-1 as the only authority path. No runtime import may be introduced from the advisory tooling.
4. Keep original donor repositories, licensing, original bytes and historical hash profiles. New canonical authority data must never be silently rewritten to the legacy JCS report profile.
5. Eight donor snapshots remain **quarantined in #135**, not automatically included in each executable tooling PR. Review archive value, size and license before a separate custody-only decision.
6. Commit only with a source pin, unit and negative tests, exact-head workflow receipts, and explicit limitations. A simulation is not physical hardware evidence. A publication proof is not truth of publication contents. A locally signed receipt is not an independent witness.
7. Leave Issue #1, C-GATE-001, decision binding #120, peer admission, external anchors and deployment-key custody open; tackle them in an **independent security review branch**, not in the consolidation PRs.

## Verification requirements

- Check the branch head, base SHA and every changed filename against the stated slice.
- Run the slice's targeted tests on that exact SHA; on a capable hosted runner inspect full pytest terminal summaries and root requirements, not just a green workflow check mark.
- Run full fail-closed `tools.verify_all`, lint, strict typing as applicable, wheel smoke for the proof slice, and hardware simulations for the Arty slice.
- Preserve failed candidate evidence and detect skipped or missing security gates.
- Before any merge, compare accepted slice content against combined #135 and record expected modifications; do not assume identical content across refactors.

**Standing:** E2 · W0 · O0 WITHHELD · V008 HOLD · DO NOT MERGE · PRODUCTION PROHIBITED.
