# Weaver Portfolio Curation Baseline v1.1 — Evidence-Labeled Addendum

**Cut date:** 2026-07-11  
**Parent baseline:** `WEAVER_PORTFOLIO_CURATION_2026-07-11.md`  
**Scope:** 58 GitHub repositories and 565 Google Drive assets  
**Primary candidate execution spine:** `Weaver_Os`  
**Governing rule:** No mechanism may silently convert uncertainty into authority.

## 1. Status vocabulary

Every operational statement in this addendum uses one of the following labels:

| Label | Meaning |
|---|---|
| **Verified in this pass** | Directly observed through repository, file, metadata, byte, hash, or connector evidence during this curation pass. |
| **Reported by an existing artifact** | Present in an existing document or manifest but not independently reproduced in this pass. |
| **Unverified risk hypothesis** | A plausible concern requiring fixtures, commands, outputs, and receipts before it can be asserted as a defect. |
| **Proposed operation** | Recommended work not yet executed or authorized as a final-state mutation. |
| **Blocked pending authorization** | Work was attempted or prepared but cannot complete until an access, quota, scope, or owner decision is resolved. |

## 2. Executive baseline

- The inventory contains exactly **58 GitHub repositories** and **565 Google Drive assets**. **[Verified in this pass]**
- `Weaver_Os` is the primary candidate execution spine. Its reviewed `main` pin is `0823452e63d13bae5f1945fced2f5d01370e7a34`. Authority remains `NONE`; deployment remains `HOLD`. **[Verified in this pass]**
- Eight repositories form the active crown-jewel set; all remaining repositories are explicitly contained as candidates, external donors, research/mythos, or quarantine/supersession candidates. **[Verified in this pass]**
- Existing portfolio artifacts report E2/E3 evidence pockets for specific components. This pass did not independently reproduce every reported Shock Kernel, GORR, hardware, or semantic-filter claim. **[Reported by an existing artifact]**
- Drive upload attempts for the curation ledgers returned `storageQuotaExceeded`. Per-file move attempts for the prepared quarantine and Folium assets separately returned `appNotAuthorizedToFile`. These are distinct demonstrated blockers. **[Verified in this pass]**

## 3. Repository directory

### Tier A — Crown Jewels / active core (8)

`Weaver_Os`, `cathedral-verified`, `Lumen`, `Weaver--Cathedral-`, `Math_Build1994`, `AutoProof`, `agency-agents6`, `zorel-kernel`

**Status:** **[Verified in this pass]**

### Tier B — Candidate engineering (9)

`A.G.I-Seed-`, `Delta-717`, `t81lib`, `t81-hardware`, `t81-benchmarks`, `ternary`, `ternary-tools`, `trinity-pow`, `SynthaMed`

Keep these repositories outside active portfolio marketing until each has an explicit checkout pin, toolchain environment, build/test command, fresh transcript, artifact hashes, and bounded promotion record. **[Proposed operation]**

### Tier C — External donors and forks (20)

`AI-Research-SKILLs`, `ai-agent-terraform`, `ai-ticket`, `awesome-agent-skills`, `claude-code-best-practice-Codex-`, `FreeLattice`, `Gbrain-Reinforced`, `hermes-agent-self-evolution`, `owl`, `rosclaw`, `ruflo`, `skills`, `strix`, `SuperAGI`, `swarms`, `system-prompts-and-models-of-ai-tools`, `t81-docs`, `t81-foundation`, `t81-roadmap`, `tinyclaw`

`ai-mesh` is excluded because it was not one of the 58 inventoried targets. Preserve upstream license history and immutable commit pins. **[Verified in this pass]**

### Tier D — Research, concept, and mythos archive (16)

`ANGELA`, `Delta-RPM-Protocol`, `duotronic-computing`, `Echo-Root-Ve-Protocol`, `LogOS`, `Lumen-Elpis`, `OpenMythos`, `Ouroboros`, `Pandora`, `Quillan-`, `Quillan-v4.2-repo`, `reson8-Labs`, `SpiralSafe`, `Sym-Chaos-`, `trinity`, `Weavers-Forge-`

Preserve for research, history, or creative continuity; keep outside active engineering navigation and authority paths. **[Verified in this pass]**

### Tier E — Quarantine and supersession candidates (5)

`AGI-to-ASI-TRANSITION-PROOF-LAYER`, `meta-meme`, `n00b`, `solfunmeme`, `spiralsafe-mono`

Permanent purge remains disabled. **[Verified in this pass]**

## 4. Direct comparison: Weaver_Os PR #4 vs PR #5

### Method

Both PR head trees were read at their immutable head SHAs. Their changes were compared against the recorded base, then all changed files were fetched and compared line-by-line after whitespace normalization. Exact paths, additions/deletions, nontrivial exact-line overlap, and vocabulary overlap were inspected. **[Verified in this pass]**

| Property | PR #4 | PR #5 |
|---|---|---|
| Title | `docs: add Cathedral-Sentinel-Weaver continuity artifacts` | `docs: add Weaver-Lumen vFinal handoff baseline` |
| Head SHA | `49c4970689203ec4667f99393479feeda6c3c03b` | `baa7bee11aa97fb9525cfb5c9bfe2fc4e00d2134` |
| Recorded base SHA | `ff99da4fb8cd4eceda2898a9f61d2743290f3fde` | `ff99da4fb8cd4eceda2898a9f61d2743290f3fde` |
| Commits | 6 | 9 |
| Changed files | 6 | 9 |
| Line changes | +915 / -1 | +1005 / -0 |
| Current connector mergeability | mergeable | mergeable |

### PR #4 changed paths

- `.github/workflows/tests.yml`
- `docs/cathedral/MUST_KEEP_REGISTRY.md`
- `docs/cathedral/REALITY_GATE_V2.md`
- `docs/cathedral/ROADMAP.md`
- `docs/cathedral/STATUS_LEDGER_ALIGNMENT.md`
- `docs/cathedral/VERIFY_ADAPTER_PHASE1_SPEC.md`

PR #4 is not strictly documentation-only: it changes the test workflow to capture verbose pytest output and upload that output as a CI artifact. Its other unique value is the Phase 1 verification-adapter specification, Reality Gate requirements, status-ledger alignment, roadmap, and large must-keep registry. **[Verified in this pass]**

### PR #5 changed paths

- `CLAIM_DOWNGRADE_LOG.md`
- `INVARIANTS.md`
- `MVP0_REPLAY_CHECKLIST.md`
- `REGISTRY.md`
- `REGISTRY_SUPERSESSION_LEDGER.md`
- `docs/HANDOFF_vFINAL.md`
- `docs/SDA_WEAVER_EVIDENCE_SPINE_INTEGRATION.md`
- `docs/WEAVER_OS_FINAL_PROFESSIONAL_HANDOFF_PACKAGE.md`
- `docs/sda_integration_registry.yaml`

PR #5 uniquely contributes claim-downgrade governance, constitutional invariants, the MVP-0 replay checklist, a concise evidence registry, a registry supersession ledger, and SDA/handoff integration material. **[Verified in this pass]**

### Line-by-line result

- Exact changed-path overlap: **0 files**.
- No substantive copied passage was found across the two PRs after normalized line comparison.
- The only exact nontrivial repeated lines detected were generic headings such as `Final compression` and `Acceptance criteria`.
- The strongest vocabulary overlap was between PR #4's must-keep registry and PR #5's final handoff, but the token-set similarity remained low (`0.167`) and did not indicate duplicate source text.

### Decision

Do **not** deprecate either PR by title or merge either branch wholesale. Preserve PR #4's adapter/Reality Gate/ledger/CI-artifact work and PR #5's downgrade/invariant/replay/supersession work. Rebase both against current `main`, then consolidate selected files in a new review branch. Treat PR #5's concise registry as the candidate current registry and PR #4's 538-line must-keep registry as a historical catalog until a field-by-field supersession review is complete. **[Proposed operation]**

## 5. Folium CXVI–CXVIII mapping

The three Folia are not three independently titled Drive documents. They are contained together inside one generic Google Keep export, while a second document discusses CXVI. **[Verified in this pass]**

| File | Confirmed contents | Original parent | SHA-256 of text export | Move status |
|---|---|---|---|---|
| `1J8g3nxcPgdqEnspYHrsPJBpSjJn1KOR7m1iXf-XeRJA` — `Google Keep Document` | CXVI: Synthesized Metaphysical Framework; CXVII: Vatican Node / Black Nobility; CXVIII: Operation Pale Ledger | `0AJ-Uq70lSEk-Uk9PVA` | `2b40fa394a36799c6d9dcb1678a4f56673ee36802bfb48f57ae303d9b065a8ce` | `BLOCKED_APP_WRITE_AUTH` |
| `1KJGhyIMSX0G4Oy5ZTDOhflpcNzRWIZ2uyAut7dY_IBY` — `Deep Dive: The Mythos and Esoterica` | CXVI-oriented mythos analysis | `1MwGp6AOhmdhl9zsNNbMUjt6M7yK7JUnK` | `3c24ad78e67556cad4471003c88443700d4ec438a0902e40816f6969d785ddba` | `BLOCKED_APP_WRITE_AUTH` |

Both files are owner-only according to visible permission metadata. Moves into `05_MYTHOS_ARCHIVE` were attempted after hashing but were rejected because the app lacks per-file write authorization. The files remain at their original parent IDs; no copy or deletion occurred. **[Blocked pending authorization]**

## 6. Cisneros interface-footprint audit

### Search result

A Drive content search returned nine candidates. Direct content inspection confirmed literal Cisneros references in five and found zero literal occurrences in four broad-index matches. Search inclusion alone is not treated as a relationship or authorization record. **[Verified in this pass]**

| File ID | Title | Literal-reference result | Visible sharing state | Authority conclusion |
|---|---|---:|---|---|
| `1on2hS7pdPiOapoxVZJqZxTl1ZCSe1CWVaVR4UgNE_Co` | `PDF Information Gathering Report - First Batch` | 2 | Not shared; owner-only metadata visible | No active external share observed |
| `1ZOoUIQlATov5KUd3CNBrPqQQIMgB3b_D` | `Epistemic.pdf` | 4 | Shared; target identities unavailable; current user cannot manage sharing | Active target cannot be established from available metadata |
| `1jtwDNp_Zh1xlAOK_O4qUkXq9ex2Z97-PkXCdJnOpSZk` | `Report` | 1 | Not shared; owner-only metadata visible | No active external share observed |
| `1BVV16cwEbOzMUfzwisPXsJbX2vrvWT12` | `SDA_251222_182309.pdf` | 1 | Shared; target identities unavailable; current user cannot manage sharing | Active target cannot be established from available metadata |
| `1z4q2wutJkoFwIOLfRZkQlBTZXYo4QuyJ8YHh8ZhQt_I` | `Google Keep Document` | 1 | Not shared; owner-only metadata visible | No active external share observed |

The four broad-index matches with zero literal occurrences were `dual (3).pdf`, `Labyrinth-OS-Agent-v5.txt`, `Labyrinth-OS-Core-v8.txt`, and `Labyrinth-OS.txt`. They are not promoted to confirmed footprint entries. **[Verified in this pass]**

No formal dissolution, revocation, or complete access sweep was established or executed. The two shared PDFs require owner/provider-side permission inspection because target identities are not visible through the current access path. **[Blocked pending authorization]**

## 7. Drive blocker matrix

| Blocker | Demonstrated scope | Current result | Required next step |
|---|---|---|---|
| Per-file app authorization | 18 hash-qualified quarantine candidates, 3 high-value control documents, and 2 Folium documents | `appNotAuthorizedToFile`; files remain at original parents | Grant the connected app access to each intended file, then repeat move and verify parents |
| Drive storage quota | Uploading the curation ledger and quarantine manifest to Drive | `storageQuotaExceeded` | Free storage or increase quota before retrying uploads |
| Share-target visibility | Two confirmed Cisneros-reference PDFs | Shared status visible; target identities and management unavailable | Inspect permissions through the owning account/provider and produce a scoped access receipt |

No global Workspace Admin override is assumed to solve the per-file authorization blocker. **[Verified in this pass]**

## 8. Urgent items with corrected evidence labels

### Paraphrase-filter exposure

The reported semantic paraphrase-filter vulnerability is an **unverified risk hypothesis**. It must not be called a live defect until reproduced with concrete fixtures, exact commands, exact outputs, negative controls, and a bound validation receipt. **[Unverified risk hypothesis]**

Recommended test outcome: replace token-only admission assumptions with a deny-by-construction or mechanically validated output contract if the hypothesis is reproduced. **[Proposed operation]**

### Hardware veto latency

The `449 ns` mean veto latency and the reported `pulse_guard.v` / `tb_pulse_guard.v` contents of `lucifer_latch_hw_bench_v0.zip` were not executed in this pass. No Icarus Verilog transcript, simulator environment, testbench output, waveform, or receipt was produced here. **[Reported by an existing artifact]**

Required promotion path: locate canonical ZIP bytes, verify its hash, extract into an isolated workspace, pin Icarus Verilog, run the testbench, preserve output/waveform hashes, and distinguish simulated timing from synthesized or physical-device timing. **[Proposed operation]**

### zorel-kernel integrity boundary

This pass verified that `zorel-kernel` carries an internal E3-receipted claim and that the portfolio must not inherit that label by filename or manifest alone. It did **not** independently validate the receipt chain. Integration remains blocked until source pins, receipt hashes, commands, environment, replay output, and witness independence are checked zero-trust. **[Verified in this pass]**

## 9. Controlled next actions

1. Grant per-file app access for the two Folium documents and the 18 existing quarantine candidates; rerun moves and verify destination parents. **[Blocked pending authorization]**
2. Inspect provider-side permissions for the two shared, content-confirmed Cisneros-reference PDFs; record target identities and roles without revoking access unless separately authorized. **[Blocked pending authorization]**
3. Rebase PR #4 and PR #5 onto current `main`; build a selective consolidation PR rather than merging either historical branch wholesale. **[Proposed operation]**
4. Generate build and replay receipts for Tier B before any active marketing or Tier A promotion. **[Proposed operation]**
5. Reproduce or falsify the paraphrase-filter hypothesis with an adversarial fixture suite. **[Proposed operation]**
6. Execute the isolated Icarus Verilog loop only after canonical hardware-bundle bytes and hashes are located. **[Proposed operation]**
7. Perform an independent zero-trust audit of `zorel-kernel` before accepting any E3 or administrative-authority claim. **[Proposed operation]**

## 10. Non-actions and safety receipt

- No GitHub PR was merged or closed.
- No repository was archived or deleted.
- No Drive asset was permanently deleted.
- No sharing permission was added, removed, or changed.
- No formal dissolution or access revocation was inferred from document language.
- The hash-before-quarantine and review-before-purge rules remain intact.

This addendum narrows claims, preserves useful engineering, and records blockers without converting them into conclusions.
