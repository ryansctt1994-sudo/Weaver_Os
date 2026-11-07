# Step 1 Ratification Packet

**Status:** RATIFIED by [GD-0001](decisions/GD-0001.md), single steward, 2026-11-07. `C-DUAL-001` limitation recorded
**Outline step:** 1 of 9 ("Ratify the frame") in
[`docs/architecture/UNIFIED_SYSTEM_OUTLINE.md`](../docs/architecture/UNIFIED_SYSTEM_OUTLINE.md)
**Authority:** O0. Preparing, merging, or passing CI on this packet does not ratify it.

Portfolio coherence rule 8: *candidate registries and architecture proposals cannot
ratify themselves.* This packet prepared the decisions. The owner made them in GD-0001.

## What is prepared

| Item | File | Checked by |
|---|---|---|
| Evidence crosswalk | `governance/evidence_crosswalk.json`, `governance/EVIDENCE_CROSSWALK.md` | `python -m tools.check_evidence_crosswalk` |
| Layout and import rules | `governance/adr/UADR-0001-trust-domain-layout.md` | `python -m tools.check_trust_domains` |
| License review | `governance/LICENSE_REVIEW.md` | factual record |

Both checkers run in `pytest` (`tests/test_evidence_crosswalk.py`,
`tests/test_trust_domains.py`) and through `make check-frame`.

## Decisions needed

| ID | Decision | Options | Outcome (GD-0001) |
|---|---|---|---|
| D1 | Adopt R0–R6 as the evidence axis with the floor-mapping crosswalk | adopt / amend / reject | **adopted** |
| D2 | Define W and O rungs above zero | define now / defer | **deferred**: W0 and O0 stay the only legal values |
| D3 | Adopt UADR-0001 domains and import rules | adopt / amend / reject | **adopted** |
| D4 | License path for moved Lumen code | A keep Apache-2.0 / B relicense MIT | **A** |
| D5 | Who ratifies, given `C-DUAL-001` (dual-steward approval not enforceable) | owner + recorded second steward / owner alone with the limitation recorded | **owner alone**, limitation recorded; ratified in `SINGLE_STEWARD` mode |

## How it was recorded

1. [`governance/decisions/GD-0001.md`](decisions/GD-0001.md) records D1–D5 and the
   `C-DUAL-001` limitation.
2. `evidence_crosswalk.json` is `RATIFIED`, mode `SINGLE_STEWARD`, decision `GD-0001`. The
   checker accepts single-steward mode only with exactly one steward and a limitation
   naming `C-DUAL-001`.
3. `UADR-0001` is `ACCEPTED`, referencing GD-0001.
4. `C-LADDER-001` is `RESOLVED` in [`CONTRADICTIONS.yaml`](CONTRADICTIONS.yaml).

Once `C-DUAL-001` is resolved, a later decision can re-ratify the frame in `DUAL_STEWARD` mode.

## What ratification does not do

It does not raise the evidence level, witness level, or authority level of any artifact.
Portfolio state stays `E2 / R2[self] · W0 · O0 · production prohibited`.
