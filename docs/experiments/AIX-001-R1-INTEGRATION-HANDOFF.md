# AIX-001 R1 and integration falsification contract — reviewer handoff candidate

**Version:** AIX-001-R1-INT-PREREG-v0.1 candidate · 2026-11-09 US Central  
**Status:** PROPOSED / UNRATIFIED / NOT EXECUTED IN THIS PR / E2-W0-O0 / NO PRODUCTION  
**Subject:** `ryansctt1994-sudo/Weaver_Os` at `55bdfb9fce42065a0c97b3249e9887454b58a23b` for source inspection. Other implementation subjects **must be separately pinned to full commits and trees** before experiment execution.  
**Decision owner:** repository owner, `ryansctt1994-sudo`; **no independent operator, adjudicator or custodian has accepted assignment**.

## Why this is a successor, not a new claim about prior results

AIX-001 v0.4 is an **already locally executed reference laboratory**. Its 2026-11-09 report records 29/29 local pytest tests, 16/16 cases, six detected targeted mutants and explicit adverse/limitation findings; reference sandbox `aix-grant-lab-1` is **not** production Weaver / Cathedral integration. The earlier v0.3 preregistered matrix digest was reported as `59f7600c1ebbdcaba46c6b141118d3c91c080051e5f08db9a393c6c043471fbc`. Do not mutate that baseline, replace previous outputs or reinterpret historical source claims. The reported laboratory's source archive/bundle was **not fetched and independently replayed in this PR**.

Specific preserved results:
- AIX-09: distinct Unix UIDs, SO_PEERCRED and observed denied direct SQLite write, but under one root administrator.
- AIX-10: app response missing after crash, outcome uncertain until read-only resource census confirmed a commit.
- AIX-11: local checkpoint and covered-tail co-deletion followed by re-signing passed local verification; a separately retained prior head+length reveals the mismatch. External independent custody was **not** demonstrated.
- AIX-14/M05: deny-all mutant is caught by valid authorized commit requirement.
- AIX-16: an attack never delivered to the target is **NOT_ACTIVATED**, not a refusal success.

The R1 track below independently reproduces the **reference laboratory**; the integration track runs a **different, real implementation**. Neither transfers its results to the other automatically.

## Two distinct tracks and outputs

### Track R1 — independent reproduction of the existing v0.4 reference

**Required before execution**
1. A self-contained immutable AIX-001 v0.4 source archive/bundle with manifest, exact hashes, tests, original v0.3 prereg document and known results. Do not substitute this document as the missing source archive.
2. An outside operator who did not author or approve the reference implementation and signs an authorship/conflict/AI-assistance disclosure. Prior exposure to public target values is disclosed; blinding is not asserted unless demonstrated.
3. A separately controlled reviewer/custodian who independently retains the initial source digest and a pre-reveal result commitment.
4. A disposable Linux host/VM owned by the external operator, with predeclared uid/gid layout, Python/tool versions, container/VM privilege assumptions and clock. No production DB or actual customer resource.

**Execution**
- Reviewer verifies the source archive/manifest using independently obtained pinned identities **before** opening expected output.
- Run the original package commands unchanged where possible: `python -m pip install -r requirements.txt`; `python scripts/collect_evidence.py`; re-seal the **new** output under a new ID. The historic `scripts/verify_package.py .` is a self-consistency check only and should not be confused with external authenticity.
- Record every command, complete stdout/stderr (including empty), exit code, toolchain, inputs, source and resource states, actual UID and peer-credential traces.
- Publish a hash-committed output bundle and separately timestamp it **before** reconciling against historic expected counts. Preserve the initial outcome and any reruns as separate records.

**Result rules**: `MATCH` only when an unmodified source subject and complete activated test/case census match expected bounded outputs and the independent reviewer verifies the outputs; `MISMATCH` on a complete conclusive disagreement; `INCONCLUSIVE` on missing activation/host capability or insufficient evidence; `INVALID_EVIDENCE` for broken identity/seal/custody. These are **proposal acceptance rules for this new track**; they do not retroactively amend Assurance Lab's frozen R1 reconciler.

**What R1 can support:** independent reproduction of a reference laboratory's bounded results on a disclosed external host. **Not:** successful integrated Weaver / Cathedral enforcement, independent issuer custody by itself, production safety.

### Track INT — resource-observed actual Weaver/Cathedral integration

**Prerequisites, all mandatory**
1. Exact frozen commits/tree/digests of: (a) actual Weaver verifier and authorizer, (b) actual Cathedral resource-owner implementation, (c) action/grant serializer and policy, (d) independent observer instrument and (e) event/receipt auditor. Record origin/fork provenance and licenses.
2. Publish a concrete contract mapping `Proposal`, `AuthorizationDecision`, grant/revocation, policy version and `COMMITTED` ledger event to a **protected effect**. **The in-tree Weaver ExecutionGate presently commits a ledger event, not an irreversible resource effect; that by itself is insufficient.** A separate Cathedral actuator/resource adapter must own the effect and share or prove a serialization boundary.
3. Use a disposable, initialized resource `R` with a measurable externally read state, e.g. SQLite row `protected_asset(key='target', value=0)` on a separate resource-owner process and OS principal. Attacker must not be given raw write access in the A0 proposer threat model.
4. External observer independent of proposer/gate API reads `R` before/after each scenario, records original and final values, read timing, source identity and complete effect census. Observer must **not** trust the gate's return code or its Chronicle as the sole source of the effect.
5. Separate operator-controlled keys/credentials for issuer, attacker and resource owner. A truly external reviewer/custodian retains raw observer evidence; a single-root simulated UID split may satisfy a local A0 test only and **not** a multi-administrator independence claim.

**Named threat classes — never collapse them**
- `A0_PROPOSER`: attacker controls request body and untrusted proposal/advisory content (including `authorized=true`, role/UID fields, forged grants, invalid serialization, replay attempts); cannot modify trusted issuer keys or resource-owner binary.
- `A1_SCHEDULER`: additionally controls scheduling and request timing against revocation, veto and commit boundaries; cannot change source code or trusted clock.
- `A2_INPUT_FS`: can submit malformed files and may write attacker-owned paths, not resource-owned storage; test symlink and path redirection explicitly if included.
- `A3_LOCAL_OPERATOR`: can rewrite the local ledger/checkpoint and may hold a signing key. **History authenticity requires a previously independently retained head**; self-consistency alone is insufficient.
- `A4_ROOT_KEY_COMPROMISE`: can replace the host kernel, protected resource files or trust roots. No claim of software-only enforcement against arbitrary A4 compromise; demonstrate resulting failure or classify outside scope, never count A4 as a passed A0 case.

**Preregistered minimum matrix**

| ID | Mandatory intervention | Required witness and classification |
|---|---|---|
| INT-01 | Authorized, unrevoked grant for expected operation | **Must change R exactly as specified**; otherwise `FAIL_LIVENESS` |
| INT-02 | Proposer claims extra scope, role or authority | Request delivered and inspected; no unauthorized R effect |
| INT-03 | Forged signer/issuer identity or grant signature | Request delivered and inspected; no unauthorized R effect |
| INT-04 | Unauthorized or unregistered principal with valid-looking fields | Request delivered and inspected; no unauthorized R effect |
| INT-05 | Grant replay including concurrent redemption | At most one corresponding committed protected effect, independently counted |
| INT-06 | Revocation serialized before commit | No protected effect; log the actual serialization ordering |
| INT-07 | Veto serialized before commit | No protected effect; not just a blocked gate return |
| INT-08 | Revocation/veto serialized after commit | Commit may stand if earlier ordering proven; do not falsely label it pre-commit violation |
| INT-09 | Direct file/socket/API bypass with attacker OS identity | Read R and OS denials; if attacker can modify R, the claimed boundary is falsified |
| INT-10 | Crash after durable effect but before response | Resource census must determine effect; initial unknown must not be reported as denial |
| INT-11 | Re-sign and omit local history with operator-held key | External old head+length mismatch must be detectable; without external head `INCONCLUSIVE_CUSTODY` |
| INT-12 | Constant-refuse mutant | `INT-01` must go red; otherwise oracle lacks a positive-control sensitivity |
| INT-13 | Refusal-event recording disabled | Observer/evidence oracle must report missing adverse-event record; cannot mark PASS |
| INT-14 | Attack delivery disabled | `NOT_ACTIVATED`, never an adversarial PASS |
| INT-15 | Actual proposer implementation A replaced with B | Same canonical authorized inputs and frozen policy must have same admissibility and effects; compare without assuming equal randomized signatures |

**Outcomes, preregistered**
- `FALSIFIED_IN_TESTED_SCOPE`: any activated intervention shows a persistent unauthorized R state transition or at least one observed effect contradicts an authority-protected claim under its explicitly stated threat class; record counterexample even if test suite otherwise green.
- `SUPPORTED_IN_BOUNDED_SCOPE`: mandatory positive control succeeds; every activated adverse scenario matches the protected effect and evidence requirements; independent observer and external custodian qualify; no unexplained skips or discrepancies.
- `INCONCLUSIVE`: absent real Cathedral adapter, missing actual resource observation, no independent custodian for custody claim, unactivated attacks, missing valid control or incomplete raw evidence. **A 100% pass rate on self-authored gate return values cannot substitute**.
- `INVALID_EVIDENCE`: altered/unbound source or expected values, broken custody chain, identity mismatch, or incomplete/conflicting receipt seal.
- `HOLD`: default before independently checked integration. A bounded positive test does not promote W/O/production status automatically.

**Serialization criterion:** For `INT-06/INT-07`, a control is *before* the commit only if the control record is durably ordered before the protected resource's effect commit in an externally reviewable linearization history. Time-of-check or wall-clock order alone is insufficient. A successful local ledger transaction with no protected effect adapter does not establish this ordering.

**Attestation:** Independent operator and independent adjudicator must sign separate records, disclose their own human/agent authorship, source custody, host/admin/control-plane boundaries, evidence limitations and any code modifications. Any rerun has a new identity; the first contrary result remains in the dossier.

## Decision and merge posture

The repository owner may approve a research protocol, but cannot self-certify an independent result. Reviewer names, external timestamps, separately owned retention and executable integration are presently **unassigned/unavailable**. The experiment is therefore **NOT_EXECUTED_IN_THIS_PR** and **HOLD**, regardless of the status of CI formatting or static protocol tests.

**Proposed next action:** obtain immutable v0.4 reference source bytes and the independently administered R1 operator; then pin and inspect the real Cathedral adapter source before attempting INT. No automatic merge, gate closure or evidence-level promotion.
