# IR-001 — Independent clean-room reproduction contract

**Status:** PROPOSED / DESIGN-ONLY / NOT EXECUTED  
**Version:** 0.1, 2026-11-09  
**Authority:** NONE. **Witness:** W0. **Operational authority:** O0. **Production:** PROHIBITED.  
**Intended classification before execution:** E2 / R2[self] (same-origin evidence only).

This specification defines what an external executor must demonstrate, independently
of the repository operator, before reporting a bounded independent reproduction.
It is **not** a handoff receipt, a frozen source archive, an invitation to
self-certify, a custody grant, a second-steward ratification, or an E3.5/E4 promotion.
The external role, keys, runner and evidence storage have **not** been obtained.

Related boundaries:
[VERIFICATION_INFRASTRUCTURE](../../docs/VERIFICATION_INFRASTRUCTURE.md),
[CROSS_HOST_SPINE_RECEIPT](../../docs/CROSS_HOST_SPINE_RECEIPT.md),
[STEP7-EVIDENCE-CUSTODY](STEP7-EVIDENCE-CUSTODY.md),
[WX-CHECKPOINT-1](WX-CHECKPOINT-1.md), and
[CONTRADICTIONS](../CONTRADICTIONS.yaml).

## 1. Claim to be tested; not the claim to be inferred

**Candidate claim:** For one exactly identified source tree and declared external
environment, the documented verification gate and designated independently devised
negative controls produce the reported outputs, including observed refusals when
source bytes or the checker input are altered.

**Outside scope:** resistance to every attack, hermetic/reproducible binary builds,
author-authentication from Git SHA alone, TOCTOU freedom, Byzantine runner safety,
ledger history authenticity, independent checkpoint custody, second-steward consent,
and production authorization. More tests cannot establish an unbounded negative.

The external executor must distinguish (a) executing author-written test suites,
(b) independently designed adversarial experiments, and (c) independent custody.
None implies either of the others.

## 2. Fixed subject and immutable bytes

The review target is **one named Git checkout**, not an unspecified moving branch.
The initial proposed subject is the corrected draft PR #108 head:

| Role | Commit (Git object identity) | Intended use |
| --- | --- | --- |
| Source head | `6324c16dbbb5783b895d25e118ce816c9026596b` | Preferred IR-001 candidate |
| Baseline main | `55bdfb9fce42065a0c97b3249e9887454b58a23b` | Integration context |
| GitHub synthetic merge | `d6684eb608df108a231369049aba81d9de95366e` | Historic tested merge, **not** interchangeable with head |

The **subject_selection** in the frozen manifest must name exactly one of these
commits and its Git tree object ID. Testing multiple targets requires **separate**
subject digests and separate receipts. The synthetic merge must not be silently
reconstructed with a new commit timestamp or substituted by a later GitHub merge.

A Git commit SHA is a hash of a serialized **Git commit object**. It is not the
SHA-256 of a tarball or ZIP, and a matching commit ID by itself is not an
independently authenticated publication. The subject transport shall be a **single
immutable Git bundle byte stream** that includes the selected commit, its reachable
trees/blobs, and any required base ancestry. A source tarball is optional but cannot
replace the bundle when the verification gate requires Git provenance.

The freeze operation MUST produce these independent objects:

1. `IR001-source.bundle`: a complete, self-contained Git bundle for the
   selected commit and needed ancestry. The bundle SHA-256 is `bundle_sha256`.
2. `IR001-file-manifest.json`: a deterministic file inventory for the **selected
   Git tree**, independent of timestamps. Each tracked path must have an explicit
   repository-relative path, Git mode/type, and SHA-256 of the blob's raw bytes;
   symlinks are recorded as link objects with the raw target text as blob bytes,
   never silently dereferenced. Include path-count, selected commit, tree object,
   digest algorithm and an exact manifest-profile identifier. Reject duplicate paths
   or ambiguous Unicode/path encodings. The manifest itself is **outside** the
   inventoried tree and has a separate SHA-256.
3. `IR001-freeze-statement`: exact `bundle_sha256`, `manifest_sha256`,
   selected commit/tree, number of tracked entries, creation context, and external
   custody destination. Its bytes and signatures are separately preserved. It
   identifies the two files without a self-hash circularity.

No digest placeholder (`PENDING`, empty, null, or guessed) is a valid freeze.
A documented file ordering and canonical byte encoding are mandatory before
computing the frozen manifest hash. A Git bundle **format check**, successful
`git fsck` of the recovered objects, exact checkout of the selected commit,
and recomputation of all per-file digests are required. Also compare the complete
set of tracked paths: missing or extra tracked files are failures, not notices.

The bundle and freeze statement must reach a **custodian the author cannot
unilaterally rewrite or replace**. The external executor obtains the trust pin
(`bundle_sha256` and any signature/public-key fingerprint) **out of band**, from
that custodian—not solely from the bundle download, repository README, its own
GitHub Action, a self-hosted site controlled by the author, or a digest embedded
inside the untrusted archive. An independently held, authenticated timestamped
digest is valuable, but an author-signed tag alone does **not** provide independent
custody. If the custodian or independently pinned digest is unavailable,
**IR-001 is NOT READY** even if a clone or archive downloads successfully.

The external executor independently verifies the bundle byte hash first, then
unbundles it into an empty repository/checkout without fetching from the author
remote. If selected verification steps need network dependencies, record and
separately constrain those downloads; their integrity is not inferred from the
bundle digest. The freeze statement and manifest are untrusted until reconciled
with the independent trust pin.

## 3. Operator and environment independence

An external executor must document who controls the operating-system account,
hardware/VM, test runner, tool installation, storage, and signing key; whether
author-controlled administrators, workflows, GitHub tokens, CI secrets, images,
or scripts can alter those controls; and all material relationships with the
author. Another cloud instance controlled by the same author is **not independent**.

The external executor chooses its own scripts for SHA-256 calculation, Git
object verification, process supervision, adversarial mutation, receipt emission,
and signature generation. Weaver scripts may be **subjects of testing**, but
must not be trusted to measure the external run or to sign its result. Pin
external verifier source versions and binaries through the executor's own
channels. Declare unavoidable shared dependencies.

Record OS/kernel/architecture, runtime image identity, Python versions,
package versions **and installed distribution hashes**, Java/TLC identity,
compiler/build tool versions, Git version, env variables relevant to tests,
test entrypoints, current directory, and network dependencies. The existing
`requirements-verification.lock` pins versions but **not** distribution
hashes; this is an environmental limitation, not a hermeticity claim.

The canonical author verification entry point is:
~~~sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-verification.lock
make verify
~~~
Execute it on the **frozen selected checkout** only after verification of the
bundle and manifest. Capture full stdout/stderr, command lines, start/finish
times from the external clock, exit codes, file digests of generated reports,
and any download failures. Record whether the verifier's own clean-tree
provenance check passed; never change that check to make an archive pass.

If the PR head and GitHub synthetic merge differ, the external receipt must
explicitly say whether it tested the source head or the exact synthetic merge.
The hosted GitHub job's synthetic merge test is useful historical comparison,
not an external re-execution and not proof of the source head by implication.

## 4. Adversarial cases — external probes, not just repository tests

External probes must be prepared and executed by the external party's tooling
independently of the archive's tests. Start from a byte-identical fixture restored
after each probe. For each case save a distinct test ID, exact fixture digest
before/after, precise timing or synchronization evidence when relevant, observed
stdout/stderr and exit code, checker decision, and unexpected acceptance/refusal.

| ID | Intervention | Required interpretation |
| --- | --- | --- |
| B-00 | Untampered valid fixture verified by the designated checker | Must accept for a meaningful negative-control baseline |
| N-01 | Flip **one byte** of a source file whose original SHA-256 is recorded, leaving the signed/declared expected digest unchanged | Must refuse; acceptance is a decisive negative-control failure |
| N-02 | Introduce an existing **intermediate directory symlink** that aliases a path inside the checkout (candidate PR #108 scope) | Must refuse; acceptance falsifies that bounded path-intake property |
| N-03 | Submit external traversal, absolute path, invalid components and candidate platform-specific separators/encodings, recording OS-specific outcomes | Refuse forbidden inputs per the actual documented path contract; do not assume cross-platform behavior from one OS |
| N-04 | Submit duplicate JSON keys, non-finite numbers, malformed JSON or missing source-digest entries | Must refuse where the candidate's JSON intake contract forbids them |
| L-01 | Rewrite both source file and expected digest so they are mutually consistent | **May accept**; record as a demonstration of the missing independent origin binding, not as evidence of provenance |
| R-01 | Race the source path **after component checks but before the final open/read** using externally controlled synchronization | A confirmed accepted substituted target is a TOCTOU counterexample; a refusal is only evidence for that one schedule; an unverified race window is INCONCLUSIVE |

The candidate currently checks path components and then opens the path by name;
it does not retain a securely opened parent directory descriptor across the
whole operation. Accordingly R-01 must **not** be represented as a guaranteed
refusal merely because N-02 is green. The external executor should document
whether the timing window was genuinely reached (e.g. its independently
instrumented system-call trace). If R-01 accepts a switched target, the
security claim of race-safe source binding is **REFUTED**, even if the
reproduction campaign completed and accurately recorded the counterexample.
If the race is not attained, record `INCONCLUSIVE`; never record `PASS`.
An IR-001 receipt may truthfully reproduce the narrow N-01/N-02 behavior
while failing to establish any TOCTOU guarantee.

The operator may choose more adversarial controls but cannot remove, silently
soften, or relabel the fixed probes after observing outcomes. A test designed
after a failure must be identified as a subsequent campaign, with an unchanged
original receipt preserved.

## 5. Receipt — generated and controlled externally

The external executor's receipt must include all these fields, with an explicit
`UNAVAILABLE` or `NOT_RUN` where necessary rather than invented values:

- `schema_id: IR-001/0.1`, campaign ID, exact scope and test plan revision;
- independently controlled operator/witness ID, independence and conflict
  declaration, custodian identity, channel and key-fingerprint evidence;
- selected Git commit and tree, bundle SHA-256, manifest SHA-256, total
  tracked-file count, per-file verification count and all mismatches;
- independently verified out-of-band trust pin and its source, acquisition time,
  and signature-validation method (or a clear `NOT_READY`);
- exact commands, environment fingerprint, installed package hashes, process
  exit codes, full logs/outputs with SHA-256, and archived test/build artifacts;
- separately recorded author-suite and independent probes B-00, N-01 through
  N-04, L-01, R-01, including unexpected behavior and a reason for inconclusive
  experiments;
- external receipt creation timestamp and signing identity; signature from
  independent tooling with independent key custody, or external custody reference;
- explicit exclusions: no unbounded attack resistance, no binary bit-reproducibility
  unless measured, no independent ledger witness solely from executing this suite,
  no E3.5/production/authority promotion.

**No Weaver program inside the bundle may generate, edit, finalize, or sign
this receipt.** External receipt bytes and evidence logs must be preserved
under external write control, with a timestamped reference. A self-hash is not
an independent signature; a signature proves control of a key, not truth of
all underlying observations. Report loss of independent custody as such.

## 6. Adjudication and stopping rule

The external executor shall emit one of:

- `NOT_READY`: frozen independently pinned bundle, manifest, custodian or
  external operator prerequisites are missing.
- `REPRODUCED_BOUNDED`: byte/object verification succeeded, documented gate
  executed, B-00 accepted, mandatory N-01/N-02 (and other applicable
  contractually forbidden inputs) refused, and independent receipt exists.
  Qualify any failures, including known R-01 limits, in the narrative and
  machine-readable results; **never** infer race freedom from this status.
- `FAILED`: byte/object mismatch, prohibited negative-control acceptance
  (except documented L-01 limitations), missing required evidence, or an
  unexpected failure of a required gate.
- `INCONCLUSIVE`: an observation required for the asserted claim could not
  be made, including an unproven R-01 interleaving.

For R-01 specifically, use separate `REFUTED`, `OBSERVED_REFUSAL`,
or `INCONCLUSIVE` findings, with **no** `TOCTOU_SAFE` verdict available
from this campaign. Any material counterexample must remain visible even if
the overall bounded test suite succeeds.

The adjudicator and external executor must not increase the portfolio's
evidence, witness, or authority axes automatically. Any promotion requires
the separate, already-governed admission process, including genuinely
independent custody and the relevant contradiction closure obligations.
**C-CUSTODY-001 and C-DUAL-001 remain OPEN by default.** Executing IR-001
does not close either; `W0`, `O0`, `E3.5 HOLD` and production prohibition
persist unless a separately authorized and evidenced decision changes them.

## 7. Handoff gate / current state

No artifact named in Section 2 has been independently frozen, custodially
published, or verified in this document. No outside operator, external
signature, probe result, or independent receipt is asserted to exist.
The GitHub Actions artifact SHA-256 from the PR #108 campaign identifies the
**Actions artifact ZIP**, not a source bundle or source-file manifest.

**Before inviting an external reviewer:** independently pin a selected bundle,
create and audit the complete per-file manifest, arrange external custody,
agree to an unmodifiable adversarial plan including R-01 treatment, and verify
the recipient can receive the trust pin without relying solely on the
author's repository. Until then status is `IR-001 NOT_READY`.
