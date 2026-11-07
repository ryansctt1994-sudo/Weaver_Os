# Evidence Crosswalk (WX-CROSSWALK-0001)

**Status:** PROPOSED — awaiting steward ratification
**Machine-readable source:** [`evidence_crosswalk.json`](evidence_crosswalk.json)
**Checker:** `python -m tools.check_evidence_crosswalk` (structure only; it cannot ratify)
**Authority:** O0

This is step 1a of [`UNIFIED_SYSTEM_OUTLINE.md`](../docs/architecture/UNIFIED_SYSTEM_OUTLINE.md) §3.
It maps the four evidence vocabularies used across the portfolio onto one target ladder.
Until it is ratified, legacy labels stay where they are and are read as "legacy, unmapped".

## Rule

A legacy label maps to the **highest R level whose proof obligation it is guaranteed to
meet**. When a label could mean more, the extra has to be evidenced separately. The
`condition_for_higher` field names what that takes. Ambiguity resolves downward.

## Target ladder: R0–R6 (from Lumen-Nexus)

| Level | Proof obligation |
|---|---|
| R0 | Identifiable idea or proposal |
| R1 | Written, reviewable specification with explicit claims and boundaries |
| R2 | Inspectable implementation plus origin-controlled tests |
| R3 | Reproducible local execution bound to canonical hashes and a valid origin receipt |
| R4 | Two valid receipts from distinct screened witnesses on non-origin hardware |
| R5 | Independent reimplementation shown equivalent under the challenge suite |
| R6 | Sustained operational evidence, safety gates, accountable human authority |

Orthogonal axes kept from Weaver: **W** (witness) and **O** (operational authority).
Status is written as a tuple: `R2[self] · W0 · O0`.

## Mappings

| Source | Label | Maps to | Kind | Why not higher |
|---|---|---|---|---|
| Lumen | E0 | R0 | exact | |
| Lumen | E1 | R1 | exact | |
| Lumen | E2 | R2 | exact | |
| Lumen | E3 | R3 | exact | |
| Lumen | **E4** | **R3** | floor | Lumen E4 needs one independent machine; R4 needs two distinct witnesses |
| Lumen | **E5** | **R4** | floor | No reimplementation (R5); no production authorization (R6) |
| Weaver | E2 | R2 | exact | |
| Weaver | E2.5 | R2 | floor | No origin receipt |
| Weaver | **E3.1** | **R2** | floor | Package *structure* only, not a receipted run (see finding below) |
| Weaver | E3 | R3 | exact | |
| Weaver | E3.5 | R3 | partial | Runtime-state qualification within R3; still origin-controlled |
| Weaver | **E4** | **R3** | floor | R4 needs two receipts from distinct screened witnesses |
| Triad | HYPOTHESIS | R0 | exact | |
| Triad | REPORTED | R1 | floor | A claim is a spec only if its boundaries are written |
| Triad | VERIFIED-LOCAL | R1 | floor | No committed tests |
| Triad | VERIFIED-REPO | R2 | exact | |
| Triad | FAILED / SUPERSEDED / UNVERIFIED | status flag | — | These describe state, not evidence strength |

## Findings from building this

1. **"E4" does not automatically mean R4.** Neither Lumen's nor Weaver's E4 definition
   requires two distinct witnesses, so neither label alone meets R4. No artifact in the
   portfolio currently claims E4, so nothing is demoted today.
2. **Weaver's `E3.1` is numbered above `E3` but proves less.** The checker's monotonicity
   rule rejected a mapping that followed the label order. Ladders are therefore listed
   by proof strength, and label numbering is recorded as non-authoritative.
3. **W and O have only a zero rung.** No repository defines W1+ or O1+. Defining them is
   decision D2 in [`RATIFICATION.md`](RATIFICATION.md). Until then nothing can claim them.

## What the checker enforces

- the target ladder is exactly R0…R6, in order, each rung with a proof obligation;
- each label appears once and maps to an R level or `STATUS_FLAG`;
- mappings are monotonic within each source ladder;
- `floor` and `partial` mappings state their `condition_for_higher`;
- no legacy label maps to R6;
- a `PROPOSED` file carries no ratification data;
- a `RATIFIED` file needs a decision ID, a date, and at least two distinct stewards.

It does not judge whether a mapping is *correct*. That is the stewards' call.
