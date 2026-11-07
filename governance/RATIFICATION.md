# Step 1 Ratification Packet

**Status:** OPEN — nothing in this packet is ratified
**Outline step:** 1 of 9 ("Ratify the frame") in
[`docs/architecture/UNIFIED_SYSTEM_OUTLINE.md`](../docs/architecture/UNIFIED_SYSTEM_OUTLINE.md)
**Authority:** O0. Preparing, merging, or passing CI on this packet does not ratify it.

Portfolio coherence rule 8: *candidate registries and architecture proposals cannot
ratify themselves.* This packet prepares the decisions. The stewards make them.

## What is prepared

| Item | File | Checked by |
|---|---|---|
| Evidence crosswalk | `governance/evidence_crosswalk.json`, `governance/EVIDENCE_CROSSWALK.md` | `python -m tools.check_evidence_crosswalk` |
| Layout and import rules | `governance/adr/UADR-0001-trust-domain-layout.md` | `python -m tools.check_trust_domains` |
| License review | `governance/LICENSE_REVIEW.md` | factual record |

Both checkers run in `pytest` (`tests/test_evidence_crosswalk.py`,
`tests/test_trust_domains.py`) and through `make check-frame`.

## Decisions needed

| ID | Decision | Options | Prepared default |
|---|---|---|---|
| D1 | Adopt R0–R6 as the evidence axis with the floor-mapping crosswalk | adopt / amend / reject | adopt as written |
| D2 | Define W and O rungs above zero | define now / defer | **defer**: keep W0 and O0 as the only legal values until defined |
| D3 | Adopt UADR-0001 domains and import rules | adopt / amend / reject | adopt as written |
| D4 | License path for moved Lumen code | A keep Apache-2.0 / B relicense MIT | **A** (see `LICENSE_REVIEW.md`) |
| D5 | Who ratifies, given `C-DUAL-001` (dual-steward approval not enforceable) | owner + recorded second steward / owner alone with the limitation recorded | must be decided first; the crosswalk checker requires two distinct stewards for `RATIFIED` |

## How ratification is recorded

1. Each steward records approval of D1–D5 in a gate-decision record
   (`governance/decisions/GD-0001.md`, created at ratification time, not before).
2. `evidence_crosswalk.json` moves to `"status": "RATIFIED"` with that decision ID, the
   date, and the steward identifiers. The checker rejects this without two distinct stewards.
3. `UADR-0001` moves to `ACCEPTED`, referencing the same decision ID.
4. A new contradiction `C-LADDER-001` (four vocabularies) is recorded as resolved by GD-0001.

## What ratification does not do

It does not raise the evidence level, witness level, or authority level of any artifact.
Portfolio state stays `E2 / R2[self] · W0 · O0 · production prohibited`.
