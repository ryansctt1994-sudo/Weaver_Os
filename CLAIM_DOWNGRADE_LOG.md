# Claim Downgrade Log

Purpose: preserve honesty when a claim is reduced from stronger language to a lower evidence label.

No downgrade is punitive. A downgrade protects the repository from treating aspiration, report, or draft as verified authority.

## Downgrade Classes

| Class | Meaning |
|---|---|
| PRODUCTION_TO_PREPRODUCTION | Production claim removed until L4/L5 evidence exists. |
| VERIFIED_TO_REPORTED | Claim exists in repo/prior report but was not re-executed in the review environment. |
| REPORTED_TO_DRAFTED | Claimed artifact lacks directly inspectable repo evidence. |
| DRAFTED_TO_CONCEPTUAL | Artifact is interpretive, symbolic, or architectural framing only. |
| AUTHORITY_TO_AW0 | UI, mythos, research, or explanation layer explicitly removed from authority path. |

## Active Downgrades

| Date | Artifact / Claim | From | To | Reason | Required Promotion Evidence |
|---|---|---|---|---|---|
| 2026-06-03 | Cathedral Mesh vFINAL production readiness | Production-implied | PRE-PRODUCTION | Independent replay and production observation are absent. | L4 independent replay + L5 production observation. |
| 2026-06-03 | Broader Cathedral Mesh inventory | Canonical-implied | REPORTED / DRAFTED / CONCEPTUAL | Inventory existence is not execution evidence. | Repo inspection, tests, receipts, replay. |
| 2026-06-03 | UI and research explainability artifacts | Authority-implied | AUTHORITY_WEIGHT_0 | Explanation and visualization must not authorize execution. | None unless converted into neutral specs and gated. |
| 2026-06-03 | Hardware sovereignty RTL | Enforced-implied | DRAFTED | No synthesis, simulation, or fault-injection receipts in this repo baseline. | RTL simulation, synthesis logs, timing/fault receipts. |
| 2026-06-03 | Formal proofs | Proven-implied | DRAFTED | No proof/model-check logs attached to this repo baseline. | Lean/TLA+/Z3 proof receipts and reproducible scripts. |

## Rule

When in doubt, downgrade. Authority may be promoted only by receipts.
