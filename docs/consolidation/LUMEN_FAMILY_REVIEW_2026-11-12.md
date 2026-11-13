# Lumen, Lumen-Elpis and Lumen-Nexus: consolidation review

Reviewed 2026-11-12 against Weaver_Os `main` at `7f839efad8c273b979678b0f94e5b1175136b0ab`.
This is a source-pinned review record. It imports no donor code, raises no evidence level,
and grants no authority. E2 / W0 / O0 and V008 HOLD are unchanged.

## Result in one paragraph

Most of what is worth keeping from these three repositories is already in Weaver: the PG-001R
promotion gate (byte-identical to Lumen-Nexus `main`), the trust-domain layout, and the
evidence crosswalk that maps Lumen's E-levels and Nexus' R-ladder. The donors' runtime pieces
(Lumen's Chronicle, receipt, verifier, veto and replay cache; Nexus' in-memory receipt ledger)
are weaker than Weaver's equivalents and are not imported. What the review *did* produce is
three defects in Weaver `main` itself, each found by checking a donor weakness against
Weaver's own code. They are fixed in the same change as this record.

## Sources reviewed

| Repository | Ref | SHA |
|---|---|---|
| Lumen | `main` | `4a3240c4f47ca0e5cd9fc7423298c3b3c00db3bf` |
| Lumen | PR #1, #2, #4, #5, #7 (open) | `0eccff8449ef3f2a27c79a179c4b7027d15c9364`, `ec44e72519f90487fd438e9affb062de1b7be354`, `2cee68b4ecc13021636c1721bb26d4c9072c7f55`, `00bb85900a67ab337918d138b1caf0673c5ceddc`, `7deeca5491153ffcbb6f2c815311fb5eefd7ce35` |
| Lumen-Elpis | `main` (README and license only) | `bacc257ad1a018dff217cfb197f9ece8346542b7` |
| Lumen-Elpis | PR #1, #3 (open; #3 stacks on #1) | `3d3df36991a3e12cf7f64314afbd26ef90257e4d`, `282ecf8bdf18c5785462ada5ee5440f18aa9e244` |
| Lumen-Nexus | `main` | `93689d76431e796a63379a7019e4528d384a87be` |
| Lumen-Nexus | PR #29, #30, #31, #32 (open) | `7817278b8e9c38f4d491b0c25d979dc73d6bac1d`, `305a7df4af24d7794cdae9f2ca8d938982622f47`, `98b2f94802b1b35a5666f5dbd7c43a96725166c6`, `e6bfe7594092d795709aa3bb0d4f00cb483448c9` |

Licensing: Lumen-Nexus and Lumen-Elpis are MIT. Lumen is Apache-2.0 and is a GitHub fork of
`symmindprotocol618-dev/Lumen`; `governance/LICENSE_REVIEW.md` records that as open. Nothing
from Lumen is copied here.

## Each donor's own checks, rerun at the pinned SHAs

One Linux host, CPython 3.13, same operator; not independent reproduction.

| Source | Result |
|---|---|
| Lumen `main`, PR #1 | 13 passed; demo, E3 package generation and verification pass |
| Lumen PR #2 / #4 / #5 / #7 | 23 / 30 / 25 / 45 passed; demo and E3 package steps pass |
| Lumen-Elpis PR #1 / #3 | 3 / 27 passed |
| Lumen-Nexus `main`, PR #29, #31, #32 | boundary check, PG-001R manifest and 19 conformance tests pass; tool suites 21 / 30 / 25 / 26 pass; PR #29's ledger and boundary tests 51 passed |
| Lumen-Nexus PR #30 | **Its PG-001R manifest check fails**: the PR edits `governance/artifacts/PG-001R.md`, which the manifest covers, without updating the manifest (size mismatch) |

## Defects found in Weaver `main`, fixed with this record

1. **`parse_strict` had no nesting bound.** `canonicalize` refuses any value nested more than
   256 levels deep, but the WX-CJSON-1 strict reader had no limit: it accepted documents the
   encoder could never produce and, from about 2,000 levels on Python 3.10, 3.12 and 3.13, let
   `RecursionError` escape instead of `CanonicalizationError` (and `is_canonical` raised instead
   of returning `False`). Every strict reader in the donor family has the same defect (below),
   as did the V008 owner (#134). The reader now applies the encoder's limit exactly, refuses
   over-deep text before the recursive parser runs, and reports a parser `RecursionError` as
   the ordinary error. `governance/specs/WX-CJSON-1.md` now states the rule; it had not.
2. **PG-001R evaluated ambiguous requests.** Weaver's `pg001r.py` is byte-identical to Nexus,
   whose `main()` reads requests with plain `json.loads`. A request that lists an open
   contradiction and then repeats `open_contradictions` as an empty list is evaluated as
   *eligible*: a reviewer reads a blocker (B03) that the gate never sees. A deeply nested
   request crashed with the same exit code as "blocked". Because the moved module is pinned
   by `tests/verifier/test_pg001r_identity.py`, it is left untouched, and
   `weaver_verifier.pg001r_request` is added as the supported entry point: strict reading,
   then the unchanged contract and evaluator, with exit codes 0 eligible, 1 blocked,
   2 rejected.
3. **Two trust-domain checker gaps.** Lumen-Nexus PR #29 repaired a from-import bypass in
   Nexus' boundary checker. Probing Weaver's separate checker with the same forms showed that
   bypass does not apply here, but two others did: a module named only at run time
   (`import_module(name)`, `__import__(name)`), and process execution or file mutation through
   `os` (`os.system`, `os.exec*`, `os.unlink`, ...) from the read-only `contracts` and
   `verifier` domains. New rules `DYNAMIC_IMPORT` and `IO_CAPABLE_CALL` refuse them. Neither
   fires on `main` today; both were also checked against draft #135's tree, which passes.

Each guard has its own test and its own mutation in `tools/check_verifier_mutations.py`.

## Defects in the donors (recorded, not fixed here)

| Where | Defect | Status there |
|---|---|---|
| Lumen `main` `WeaverVerifier` | An empty, present ledger authorizes an arbitrary receipt; a receipt with a forged actor and stale `receipt_hash` is authorized | Fixed on draft #7 (receipt hash recomputed, claim bound, 64-hex replay tip required) |
| Lumen `main` `Chronicle` | Resumes over a corrupted ledger and appends; crashes on a non-object line; admits `NaN`; two writers fork the file | Fixed on draft #7 |
| Lumen draft #7 `Chronicle` | Dropping the newest entries still verifies (no anchor); a deeply nested line crashes `verify` and construction with `RecursionError` | Open |
| Lumen-Elpis #3 `load_request` | A deeply nested request raises `RecursionError` (non-objects, duplicate keys and `NaN` are refused cleanly) | Open |
| Lumen-Nexus PG-001R CLI | Duplicate keys resolved silently; deep nesting crashes; crash and "blocked" share exit code 1 | Open; Weaver's copy shares it, closed here by the strict entry point |
| Lumen-Nexus #30 | PG-001R manifest not updated for an edited covered file | Open; its own conformance check fails |

## Dispositions

| Component | Disposition | Why |
|---|---|---|
| Nexus PG-001R contracts, evaluator, conformance suite | Already in Weaver | Byte-identical to Nexus `main` |
| Nexus trust-domain layout, contradiction format, R-ladder crosswalk | Already in Weaver | UADR-0001, `governance/CONTRADICTIONS.yaml`, `governance/EVIDENCE_CROSSWALK.md` |
| Lumen Chronicle, receipt, `WeaverVerifier`, simulated veto, replay cache | Not imported | Weaker than Weaver's ReceiptLedger, signed grants, RTL-matched latch twin and replay cache; licence open |
| Nexus #29 single-owner receipt ledger | Not imported | In-memory only; Weaver's ledger is persistent, transactional and anchored |
| Lumen #2 identity-continuity probes | Reference only | The external-checkpoint checks are what Weaver's anchors already do; its counterexamples (truncation, coherent forged chain, empty history, unwitnessed self-report) are a checklist for ledger tests |
| Lumen #1 integration-intake registry | Reference only | Its "required before enablement" fields (upstream commit, licence, copied paths, negative tests, non-claims) are a good checklist for future donor imports |
| Lumen-Elpis escalation outbox | Reference only | Exclusive-create, review-only decisions; E2 scaffold with no consumer in Weaver |
| Lumen continual-learning policy, provider interface, skill manifest, FreeLattice adapter | Not imported | Threshold rules and interfaces with no Weaver consumer; principle already in `docs/architecture/UNIFIED_SYSTEM_OUTLINE.md` |
| Nexus #30–#32 (PG-001 history, Gate Zero workflow, PG-001 import admission) | Not applicable | Concern the lost historical PG-001 and Lumen's CI, not Weaver code |

## What this does not do

- It does not import, vendor or relicense donor code.
- It does not establish that the donors' remaining open defects are fixed upstream.
- The trust-domain checker stays a static syntax check: aliasing the import function or
  `exec` still escapes it, and writes through `open(..., "w")` or `pathlib` are not detected.
- Same operator, one host, plus the repository's own CI: not independent validation.
