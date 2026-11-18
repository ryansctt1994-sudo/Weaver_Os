# WC-4R-001 v0.2 — First source-pinned defect cycle

**Status:** research-only candidate · no promotion · O0 WITHHELD · production prohibited.

## Scope of this upgrade

- Preserves original `catalog.json` and the empty v0.1 `events.jsonl` for backward reference.
- Adds `ledger_v02.py`, `events-v02.jsonl`, `defect-events-v02.jsonl` and CI validation.
- Each execution event has separate **execution outcome**, **evidence completeness**, and **independence class**.
- Event bodies are SHA-256 committed using sorted-key compact JSON, with explicit previous-event links. The first previous hash is 64 zero hex digits.
- A valid `repair_of` links a fresh PASS to an earlier FAIL of the same catalog family, original source SHA and regression selector, but a different code target SHA.
- Defect lifecycle is strictly `OPEN → REPRODUCED → PATCHED → REGRESSION_PASS → REVIEWED → CLOSED`.
- The first defect deliberately stops at `REGRESSION_PASS`: **there is no independent review or closure**.

## AL-SNAPSHOT-001 (first live record)

- Source defect: https://github.com/ryansctt1994-sudo/Assurance-Lab/pull/3
- Source baseline: `ba10a0c3d58e9ea2663e6b73dc763bee4bc29404`
- Repair (already proposed upstream): `deabdad605d3536a7b55110c63404abe64eecc9e`
- New replay workflow PR: https://github.com/ryansctt1994-sudo/Assurance-Lab/pull/7
- Fresh owner-controlled CI run: https://github.com/ryansctt1994-sudo/Assurance-Lab/actions/runs/43503774619
- CI replay on identical pinned regression `tests/test_al_snapshot_001.py`: **baseline 7 FAIL, 1 PASS with KeyError; repaired 8 PASS**.
- GitHub retained artifact `al-snapshot-001-pinned-replay`, reported artifact SHA-256 `da1e4a7d00ca6b0656dc835c8b1f9f0b8fe2bd2c9ffbaa46f488f41f6ea78fc9`.
- Recorded as **two** run-level outcomes (one FAIL on the defective commit; one PASS on the fixed commit), not as sixteen independent engineering improvements.
- `evidence_status=INCOMPLETE` pending byte-level independent inspection and lasting custody of the CI artifact; `independence_class=OWNER_CI`. No witness admitted.
- AL-SNAPSHOT-001 remains a **narrow crash repair**, not full integrity/authenticity validation. The upstream PR reports accepted damaged snapshots and consistent rollback as residual risks.

## Reproduction and accounting

```sh
python governance/consolidation-v0.1/ledger_v02.py --self-test
python governance/consolidation-v0.1/ledger_v02.py
```

The v0.2 summary reports run-level attempts, outcome frequencies, evidence-status frequencies, independence-class frequencies, latest verdict per family, linked repair passes, and defect lifecycle statuses. It never derives independent-witness admission from a claimed witness label.

**Known limitations:** SHA-256 hash links detect unauthorized in-place mutation only if the trust anchor is preserved elsewhere; anyone able to rewrite the whole stream can recompute the chain or truncate its tail. A GitHub artifact digest and workflow green status do not independently verify that its bytes remain retrievable, and the artifact may expire. The reviewer identity field is not a cryptographic witness credential. Future work must add durable custody and externally anchored commitments before this becomes an authoritative ledger.

The proposed fixes remain in draft PRs; no default branch was modified or merged by this experiment.
