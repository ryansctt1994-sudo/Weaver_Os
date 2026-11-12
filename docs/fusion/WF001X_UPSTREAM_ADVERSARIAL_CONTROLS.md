# WF-001X — Source-pinned upstream adversarial controls

**State:** TEST-ONLY, REVIEW-ONLY, DO NOT MERGE. Parent WF-001 PR #130 remains blocked.
**Assurance:** E2 ceiling / W0 / O0 / V008 HOLD unchanged. No production authorization. Parent PR #130 corrective revision remains subject to exact-head CI.

## Frozen source selection

| Project | Source commit | Test origins | Translation into Weaver |
|---|---|---|---|
| ZOREL / Cathedral | `abd777e43906cd7bacbd210a5975665730446d2f` | `tests/test_actionops.py`, `tests/test_admissibility.py`, `tests/test_replay.py` | Input shape, actor and authority declaration refusal, operation narrowing, mutation isolation, canonicalization differential |
| Delta-717 | `c0a84e44967f9206fecc601acd370b5d7642fa0a` | `tests/guide/test_guide.py` | Malformed JSON and nonfinite probability metadata refusal; approval-as-advisory cannot bypass a denying Weaver gate |
| Weaver OS | `e090726a31490b8f5be9f73bad96280c10709c5a` | Original WF-001 bridge contract source |
| Weaver OS | `fffd18989708486e1970c6fdaa0a5d60b83a6a37` | Corrective parent PR #130: restricted fusion trust-domain registration and lint fixes; acceptance pending | Behavior tested on the actual Weaver modules in the CI checkout |

**Nature of the tests:** These are *scenario adaptations* referencing upstream test purposes, not copies of their entire test suites, and do not import the upstream modules into production. Upstream ZOREL semantics have no power to issue Weaver grants. Delta's `APPROVED` or `VETO` statuses remain advisory. Delta's entropy metric represents probability dispersion, **not independently validated epistemic uncertainty**.

## Commands

```sh
python -m pytest -q tests/fusion/test_upstream_adversarial_controls.py
python -m pytest -q tests/fusion
python -m tools.check_trust_domains
python -m tools.verify_all
```

The exact-source CI environment must install the locked verification dependencies and run the existing V008 isolation workflow separately. A normal unprivileged pytest result does **not** prove cross-UID security.

## Explicit non-claims

- Does not establish real isolated-owner refusal or cross-UID authority separation.
- Does not exercise signed-grant crypto validation or revocation/commit transaction racing.
- Does not imply upstream ZOREL receipt hashes are interoperable with `WX-CJSON-1`.
- Does not grant a trusted Delta decision path, import Delta's forensic ledger, or modify its entropy algorithm.
- Parent PR #130's UADR-0001 and three I001 fixes are incorporated by a two-parent reconciliation commit; their effectiveness and this PR's import-order fix still require fresh hosted verification.
- Does not promote E2, W0, O0; green tests do not authorize merge or release.

## Required evidence

Keep source-head SHA, base SHA, hosted test logs, failing checks, environment metadata and exact test counts. Preserve failed parent-revision evidence. A test-only stacked PR may remain red because of inherited parent failures; that result must be reported as red.

## Local upstream baseline

A retained ZOREL mirror in the November 12 assurance bundle was executed in an isolated local Python workspace. Its four original test files yielded **8 passed**. That is bounded local reproduction of those test files, not cross-repository integration or an independent external witness.
