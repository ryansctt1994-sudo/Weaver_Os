# Unified System Outline

**Status:** CONCEPTUAL OUTLINE · candidate architecture, not ratified
**Evidence level of this document:** E0 / R1 (specification text only)
**Authority:** O0 — none granted by this document
**Scope:** consolidation of `Weaver_Os`, `Lumen`, `Lumen-Nexus`, `cathedral-verified`, `Lumen-Elpis`
**Date:** 2026-11-07

> This outline picks the strongest piece of each repository and arranges them
> into one system. Merging code into one repository does **not** merge evidence.
> Every component keeps the evidence level it earned where it earned it, and
> re-earns it in its new location (Portfolio coherence rule 2 and rule 10).

---

## 1. What each repository brings

Observed in this session, from a fresh clone, origin-controlled (E2 / R2[self] at most):

| Repo | Real executable core | Test result observed | Best contribution |
|---|---|---|---|
| `Weaver_Os` | `triadic_controls/` (Ed25519 verifier, pinned-root key registry, SQLite replay cache, trust ledger), `policy/claim_transition.py`, `tools/` spine (fail-closed spine, authority-state reducer, runtime-state digest, spine receipts, witness-archive verify, mutation checks), `weaver_release_guard` (SLSA/OIDC provenance), TLA+ `WitnessBoundary` | `pytest -q`: 171 passed | Cryptographic authority verification, the evidence-axis discipline (E / W / O), CI-emitted receipts, formal model, release provenance |
| `Lumen-Nexus` | `lumen_contracts` + `lumen_verifier` PG-001R promotion gate; `tools/check_boundaries.py` | 40 passed | Trust-domain layout (contracts / runtime / verifier), R0–R6 ladder, contradiction registry, ADR-0006 single-owner ReceiptLedger, seal discipline |
| `cathedral-verified` | `chronicle/chronicle.py` (hash chain + head anchoring), `hardware/lucifer_latch/lucifer_latch.v` | Chronicle: 15/15 adversarial. Latch: 8/8 reported (not rerun here — no `iverilog`) | Strongest Chronicle implementation; the only hardware veto RTL; L1–L4 layered safety doctrine |
| `Lumen` | Chronicle, simulated veto, receipt, replay, SQLite replay cache, continual-learning pipeline, FreeLattice adapter, E3 package scripts | `pytest tests -q`: 13 passed (README still says 9) | Continual-learning promotion pipeline, receipt-package workflow, Must-Keep registry and gap ledger |
| `Lumen-Elpis` | none | n/a | Namespace and its promotion checklist only |

Important finding: in `Weaver_Os`, `chronicle/`, `receipt/verify.py`, and `kernel/reducer.py`
deliberately defer to the RC1 witness archive. `canonical/canonical.py`,
`policy/policy_gate.py`, `policy/signed_verifier_adapter.py`, and
`compression/residual_monitor.py` are `TODO` stubs. The anchor repo's own
source tree is therefore **missing exactly the primitives the other repos already
have**. That is the main reason to consolidate.

---

## 2. One doctrine

A single constitutional layer, assembled from material that already agrees:

```text
PRIME INVARIANT
  No mechanism may silently convert uncertainty into authority.

OPERATING THEOREM
  Cognition may propose. Only replayable evidence may authorize.
  Capability may grow internally. Authority must arrive externally.
  Reality retains veto. No receipt, no authority.
```

Constitutional invariants, by source:

| Invariant | Source |
|---|---|
| `GENESIS_IS_DECLARED_NOT_VERIFIED` (Genesis Receipt) | Weaver `METACONSTITUTION.md` |
| `FAILED_ACTIONS_ARE_NOT_STATE` / `ARE_EVIDENCE` / `REJECTIONS_MUST_BE_CHRONICLED` | Weaver `DUAL_LEDGER_MODEL.md`, CVP addendum |
| `VALID_EVENTS_IN_INVALID_HISTORIES_MUST_BE_REJECTED` | Weaver CVP addendum |
| Fail-closed: `¬constraint_ok ⇒ HARD_FAIL`; ambiguity ⇒ lowest defensible authority | Cathedral §8, Nexus `AUTHORITY.md` |
| Observer isolation: monitors have zero write rights | Cathedral §6 |
| Execution order `Observe → Authorize → Allocate → Commit` | Cathedral §3 |
| TOCTOU: `Verify → Reserve window → Execute → Revalidate → Commit or safe-abort` | Weaver triadic-controls Layer 4 |
| Cryptography proves key-signed-payload, never legitimacy | Weaver triadic-controls |
| Storage is not learning; a skill is promoted only on measured transfer | Lumen continual learning |
| `NAME != IMPLEMENTATION`, `README != EVIDENCE`, `CAPABILITY != AUTHORITY` | Elpis, Weaver |

These become one `constitution/` directory with one invariant registry (ID, statement,
source, enforcing test or `UNENFORCED`). Doctrine with no enforcing test is
labeled `UNENFORCED`, not dropped.

---

## 3. One evidence model (the biggest reconciliation)

There are four ladders today:

- Lumen: `E0–E5`
- Weaver: `E0–E4` plus `E3.5`, plus separate Witness (`W`) and Authority (`O`) axes
- Nexus: `R0–R6` with a minimum proof obligation per rung
- Weaver triad labels: `HYPOTHESIS … VERIFIED-REPO … FAILED`

Lumen itself warns not to map these by name. The unified system should
therefore **not** pick one silently. Proposal:

1. **Evidence axis = Nexus R0–R6.** It is the most rigorous: each rung has a stated
   proof obligation, and R4 requires two distinct, screened, non-origin witnesses.
2. **Keep Weaver's orthogonal axes:** Witness `W0…` and Operational authority `O0…`.
   An artifact's status is a tuple, e.g. `R2[self] · W0 · O0`.
3. **Keep the scope suffix** (`[self]`, artifact, environment, challenge set).
4. **Publish an explicit crosswalk** as a ratified governance artifact. Until it is
   ratified, legacy labels stay in place, annotated with "legacy, unmapped".

Draft crosswalk: now prepared as `governance/evidence_crosswalk.json` and
[`governance/EVIDENCE_CROSSWALK.md`](../../governance/EVIDENCE_CROSSWALK.md) (RATIFIED by GD-0001).
Legacy labels map to the highest R level they are guaranteed to meet (floor). Building it
corrected two rows of the first draft: Lumen and Weaver **E4 map to R3, not R4** (neither
requires two distinct witnesses), and Lumen **E5 maps to R4, not R6** (no production
authorization). No legacy label may map to R6.

Evidence moves only through the promotion gate (§5.6). Breaking a reproduction
path moves the claim down (Weaver downgrade rule).

---

## 4. Repository layout (Nexus trust domains, Weaver as host)

```text
Weaver_Os/                          # portfolio anchor (unchanged role)
  constitution/                     # doctrine + invariant registry + Genesis Receipt
  governance/
    EVIDENCE_LADDER.md              # R0–R6 + W + O axes + crosswalk
    CONTRADICTIONS.yaml             # merged registry (Nexus format)
    adr/                            # ADR-0006 and successors
    specs/                          # PG-001R, receipt profile, canonicalization profile
  packages/
    contracts/                      # schemas + frozen dataclasses; no project deps
    runtime/                        # stateful: ReceiptLedger, replay cache, execution gate
    verifier/                       # read-only: PG-001R, replay verify, archive verify
    learning/                       # continual-learning pipeline (runtime-side, gated)
    release_guard/                  # SLSA/OIDC provenance CLI
  hardware/
    lucifer_latch/                  # RTL + testbench (simulation evidence only)
  formal/
    tla/WitnessBoundary.*           # pinned TLC
    ccs/                            # proof obligations skeleton
  adapters/                         # FreeLattice, provider mesh, skill manifests (edge, no authority)
  tools/                            # spine, digests, mutation checks, boundary checker
  evidence/                         # receipts, manifests, baselines (non-runtime)
  audit-package/                    # reviewer-facing bundle
  operator-kit/                     # runbooks, skills, loops
  research/  archive/  legacy/quarantine/   # non-runtime; imports from here are CI failures
```

Import rules (from Nexus `check_boundaries.py`, extended):

```text
contracts  → nothing in the project
runtime    → contracts
verifier   → contracts          (never runtime: verification stays read-only)
learning   → contracts, runtime (may propose; promotion goes through verifier)
adapters   → contracts          (may only submit proposals)
research / archive / legacy / evidence → never imported by runtime code
```

---

## 5. Components: which implementation wins

### 5.1 Canonicalization (`contracts`)
One profile: RFC 8785 with Weaver's triadic restrictions (no floats, NaN or
Infinity in authority payloads, no `additionalProperties`, unambiguous timestamps,
domain-separated signing objects). Replaces the `canonical.py` stub, Cathedral's
`sort_keys` JSON, and PG-001R's `PG001R-JSON-1` (kept as a named diagnostic profile).
Needs cross-runtime test vectors (ADR-0006 requirement).

### 5.2 Chronicle + ReceiptLedger (`runtime`)
- **Base:** `cathedral-verified/chronicle.py`. It is the most complete (head anchoring,
  fsync, 15 adversarial cases).
- **Extend with:** Lumen's event-type and metadata fields, and Weaver's **Dual Ledger**
  structure (Authority Root + Rejection Root under one Chronicle Root).
- **Wrap in:** ADR-0006 **single-owner `ReceiptLedger`**. Callers submit event content
  only. The ledger alone assigns sequence, predecessor, and head. Receipts are created
  only after a successful commit. This is the concrete fix for `C-RCPT-001`.
- Receipt fields: start from Lumen `receipt.py` (actor, event hash, prev hash,
  policy version, payload hash, admissibility, replay result, verifier) validated
  against Weaver `schemas/receipt.v1.json`.
- Retire the other two Chronicle copies and the deferred Weaver stub once the
  merged ledger passes all three sets of tests.

### 5.3 Replay protection (`runtime`)
Weaver `triadic_controls/crypto/sqlite_replay.py` (atomic `INSERT … ON CONFLICT DO NOTHING`,
WAL, busy timeout). Lumen's near-duplicate is retired. The in-memory cache stays for tests only.

### 5.4 Authority verification (`verifier` + `contracts`)
Weaver `CryptoVerifier`: pinned offline root, signed `KeyRegistry`, `IssuerRecord`,
`RolePolicy`, `SignatureEnvelope`, quorum independence, lifecycle checks. It replaces
Lumen's 44-line `authority/verifier.py`. Authority levels 0–5, where Level 0 is a
quarantine state and never a grant.

### 5.5 Claim-state transitions (`verifier`)
Weaver `policy/claim_transition.py` (A1 invariant: binds the exact predecessor state and
policy head, changes one coordinate per transition). It fills the role the empty
`policy_gate.py` stub was meant for.

### 5.6 Promotion gate (`verifier`)
Nexus **PG-001R** unchanged: B01–B07 blockers, I01–I02 subset invariants, canonical
19-test suite, read-only, eligibility rather than a grant. It becomes the only path
by which anything moves up R0–R6, including learned skills (§5.9). Its identity stays
PG-001R. It is never relabeled PG-001 (`C-PR006-001`).

### 5.7 Execution gate and veto (`runtime` + `hardware`)
```text
proposal
  → contracts validation (strict schema, fail closed)
  → CryptoVerifier + replay check
  → claim transition / PG-001R eligibility
  → reserve authority window
  → veto check  (software twin of latch; RTL latch in hardware path)
  → execute
  → revalidate before irreversible commit
  → ReceiptLedger.commit → Authority Root      | any failure → Rejection Root
  → read-only replay verifier → spine receipt
```
- **Hardware:** `lucifer_latch.v` as the L1 reference: irreversible, physical reset only.
- **Software twin:** Lumen `hardware_veto.py`, rewritten to match the RTL state machine
  exactly (`ARMED → EVALUATING → TRIGGERED`, the same threshold and timing floor), with one
  shared test-vector file that both the Python tests and the Verilog testbench consume.
  This is the most direct path to the "Reality retains veto" claim being testable end to end.
- Observers and monitors have zero write rights. A write attempt is a `HARD_FAIL`.

### 5.8 Spine and digests (`tools` + CI)
Keep all of Weaver's spine tooling as is: `fail_closed_spine`, `authority_state`
reducer, `runtime_state_digest` contract, `witness_rc1_state_adapter`,
`emit_spine_receipt`, `verify_witness_archive`, `check_verifier_mutations`,
`run_adversarial_corpus`. Its separations (`LocalReducerDigest != RuntimeStateDigest`,
`make verify-e35` intentionally non-zero) are carried over unchanged. Once the merged
ReceiptLedger exists, the reducer gets a runtime source in the tree instead of
deferring to the RC1 archive. That is the honest route to an E3.5 / R3 runtime-state digest.

### 5.9 Governed learning (`learning`)
Lumen continual-learning pipeline:
`Chronicle event → Replay → ExperienceRecord → SkillCandidate → TransferReport →
MemoryUtilityReport → PromotionDecision → Skill Registry`, plus the forgetting
detector (`ACTIVE / STALE / REVIEW / DEPRECATED`). Change: `PromotionDecision` stops
being local and is computed by PG-001R. A skill is an artifact like any other.

### 5.10 Release provenance (`release_guard`)
Weaver `weaver_release_guard` (SLSA provenance, OIDC verification) and the signed
RC1 release layout (`MANIFEST.json` + `.sig` + pinned public key). This is how the
consolidated repo's own releases are bound.

### 5.11 Formal (`formal/`)
`WitnessBoundary.tla` with pinned TLC (asset ID + SHA-256), and the CCS proof-obligation
skeleton. Next model: the ReceiptLedger single-owner invariants and the TOCTOU gate.
Scope stays "bounded model of an abstraction" until a refinement argument exists.

### 5.12 Edge adapters (`adapters/`)
Lumen FreeLattice adapter, provider mesh interface, skill manifest schema, and the
Quillan evidence-graph schema. They may only *submit proposals* through the contracts
layer. They have no authority and no direct ledger writes.

### 5.13 Governance operations
- Nexus `CONTRADICTIONS.yaml` format plus its issue templates (`contradiction`, `evidence-gap`)
  and CODEOWNERS.
- Lumen **Must-Keep Registry** (Tiers 0–6) and **Implementation Gap Ledger**
  ("if listed here, zero execution authority").
- Weaver `audit-package/`, `operator-kit/`, release-readiness receipt template.
- Nexus seal discipline: `SEAL_CONDITION.md` held. No workflow may flip it automatically.

---

## 6. What does not come over as runtime

| Item | Disposition |
|---|---|
| Weaver `canonical.py`, `policy_gate.py`, `signed_verifier_adapter.py`, `compression/residual_monitor.py` (TODO stubs) | Replace with §5 implementations, or delete. No stub ships in `packages/`. |
| Weaver `chronicle/`, `receipt/verify.py`, `kernel/reducer.py` (defer to RC1) | Superseded by the in-tree ReceiptLedger. The RC1 archive stays as frozen historical evidence. |
| Duplicate Chronicle / replay cache / verifier in Lumen | Retired after parity tests pass against the winning implementation |
| Cathedral §5 integration map (`runtime_gate.py`, `constraint_engine.py`, Z3, EKF observer, `p_fail_trainer.py`, T81 ternary kernel, ML-DSA gatekeeper) | `research/`. Those files are not in any of these repos. They stay Tier 6 / R0 until code exists. |
| Cathedral "Theory ~95% / Implementation ~70%" snapshot | Archived as historical. It is not compatible with the evidence ladder. |
| `Lumen-Elpis` | Stays a namespace shell. Its 7-point promotion checklist becomes the template for adding any new package. |
| Lumen legacy `E3_CANDIDATE` labels | Re-expressed through the ratified crosswalk |

---

## 7. Provenance rules for the merge

- `Lumen` is a GitHub fork of `symmindprotocol618-dev/Lumen`. Code moved from it keeps
  upstream attribution and license (Apache-2.0) in a `NOTICE` / per-file header.
  `Weaver_Os`, `cathedral-verified`, and `Lumen-Nexus` are MIT.
  A license check is a prerequisite step, not an afterthought.
- Moved code arrives at **R1 in its new location** (specification + code present). It
  regains R2 when its tests pass in the new tree under the new import rules.
- Source repositories are archived read-only, with a pointer to the consolidated path.
  They are not deleted: their commit history is evidence.

---

## 8. Open contradictions the merged system inherits

| ID | Short form | Addressed by |
|---|---|---|
| C-RCPT-001 | receipt / hash-chain dual ownership | §5.2 ReceiptLedger |
| C-EVID-001 | unsupported audit claims | §3 crosswalk + claim-by-claim binding |
| C-PR006-001 | historical PG-001 missing | stays open. PG-001R is a successor, not a recovery |
| C-ANCHOR-001 | placeholder E4 anchors | full SHA identifiers in spine receipts (§5.8) |
| C-DUAL-001 | dual-steward approval not enforceable | governance work. Code cannot close it |
| C-LADDER-001 | four evidence vocabularies | RESOLVED by GD-0001 (single steward) |
| C-STUB-001 | anchor-repo stubs for core primitives | §5.1–5.5 (OPEN, `governance/CONTRADICTIONS.yaml`) |

Portfolio state after the merge is unchanged until evidence says otherwise:
`E2 / R2[self] · W0 · O0 · production prohibited · E4 not earned`.

---

## 9. Build order

1. **Ratify the frame.** Evidence crosswalk (§3), layout and import rules (§4), license check (§7).
   *Done: [GD-0001](../../governance/decisions/GD-0001.md), single steward, `C-DUAL-001` limitation recorded.*
2. **Contracts first.** Canonicalization profile + test vectors, receipt schema, PG-001R contracts.
   *Done: `packages/contracts` (WX-CJSON-1, wx-receipt-1, PG-001R contracts moved verbatim). Found `C-CANON-001`.*
3. **ReceiptLedger.** Merge the Chronicles into one single-owner Dual-Ledger ReceiptLedger.
   Port all 15 Cathedral adversarial cases plus Lumen's tests, then add the ADR-0006
   mutation and concurrency tests.
   *Done: `packages/runtime` + `packages/verifier` ([WX-RECEIPT-LEDGER-1](../../governance/specs/WX-RECEIPT-LEDGER-1.md)). `C-RCPT-001` stays open pending ADR-0006 acceptance and a repair receipt.*
4. **Verifier domain.** Move CryptoVerifier, claim transition, PG-001R, and replay verify.
   Extend the boundary checker. CI fails on cross-domain imports.
5. **Execution gate + veto twin.** TOCTOU gate, a Python veto matching the RTL, and
   shared test vectors with the Verilog testbench in CI (`iverilog`).
6. **Runtime-state digest from the in-tree ledger.** Retire the RC1 deferrals. Keep
   `verify-e35` red until its gates are actually met.
7. **Learning on the gate.** Route skill promotion through PG-001R.
8. **One end-to-end demo.** Weaver's four boundary-integrity cases + Lumen's full loop,
   producing one spine receipt per run.
9. **Then independence.** Clean-clone non-origin reproductions (Nexus #11/#12, Weaver
   Milestone F), and a second verifier implementation (R5 / Milestone E).

Steps 1–8 can raise components to R2/R3[self] in the new tree. Only step 9 can move
anything to R4, and no step here touches the O axis.
