# SDA ↔ Weaver_OS Evidence-Spine Integration Addendum

**Date:** 2026-06-03  
**Status:** DRAFTED / PARTIALLY IMPLEMENTED  
**Maturity ceiling:** L3 until independent replay  
**Authority impact on Weaver_OS:** none  
**Production authority:** not granted  
**Formal-security claim:** not granted  
**Evidence type:** engineering evidence only  

> This addendum records the integration between SDA — Sovereign Defense Architecture — and the Weaver_OS evidence discipline. It does not claim that SDA is provably secure, production-ready, or an alignment solution. Its purpose is to bind SDA claims to reproducible receipts, explicit downgrade boundaries, and independent replay requirements.

---

## 1. Integration Summary

SDA is a systematic security framework for conversational AI that treats constraint preservation, conversational-state integrity, and goal-level attack detection as first-class security objectives. Weaver_OS contributes the evidence spine: labels, maturity ladder, claim receipts, replay discipline, downgrade logs, and the rule that no metric should be promoted without a stable regeneration path.

The integration is operational rather than rhetorical:

- SDA supplies a concrete conversational-security workload.
- Weaver_OS supplies claim discipline, receipts, replay posture, and maturity boundaries.
- The result remains capped at L3 until independent replay in a clean checkout.

---

## 2. SDA Artifacts to Preserve

```text
SDA_MASTER.md
EVIDENCE_POSTURE.md
verify_claims.py
claims_receipt.json
docs/SDA_WEAVER_EVIDENCE_SPINE_INTEGRATION.md
docs/sda_integration_registry.yaml
figs/results.csv
figs/swmr_results.csv
figs/beta_vs_escape_rate.png
figs/wait_vs_escape_rate.png
figs/beta_vs_swmr.png
figs/regime_vs_swmr.png
```

Implemented SDA runtime artifacts to preserve:

```text
sda_runtime/cir.py
sda_runtime/drift.py
sda_runtime/budget.py
sda_runtime/aggregator.py
sda_runtime/runtime.py
sda_runtime/api.py
sda_runtime/redteam.py
demo.py
demos/adaptive_pacing.py
demos/harm_weighted.py
tests/test_sda.py
tests/test_redteam.py
tests/test_swmr.py
```

---

## 3. Bound Receipt

The SDA claim receipt is treated as a live binding, not a memory claim.

```text
claims_hash: bf25ae33…
verify_claims.py: exit 0
six headline SDA claims reproduced
hash confirmed stable against shipped claims_receipt.json
```

Promotion boundary: this receipt can support L3 evidence only. L4 requires independent replay of `verify_claims.py` in a clean checkout by a separate party or environment.

---

## 4. SDA Findings to Preserve

```text
Constraint Drift is not Topic Drift.
Goal Rewrite Attack Vector is the primary SDA threat framing.
Suspicion Budget exposes a measurable beta failure surface.
Adaptive pacing can defeat forgiving budgets.
Rule-engine backstop reduces harm-weighted miss rate.
SWMR is the preferred headline metric over raw escape rate alone.
```

---

## 5. Spec-vs-Code Gaps

These gaps must remain explicit and may not be silently collapsed into verified claims.

```text
Implemented Suspicion Budget has no SB_max cap.
Implemented risk aggregation is simplified: max(R, M, L).
Uncertainty term U is absent.
CSR is not fully implemented.
Goal Graph is not implemented.
State Integrity is not implemented.
Reward model is placeholder 0.0.
Extractor circularity remains a live attack surface.
```

Downgrade classification: DRAFTED / PARTIALLY IMPLEMENTED. These are not production defects by themselves; they are evidence boundaries.

---

## 6. Weaver_OS Discipline Imported into SDA

```text
No claim without a receipt.
No metric without a regeneration command.
No headline number without a stable hash.
No L4 claim without independent replay.
```

Concrete effect: SDA's numbers, plots, and headline claims should be regenerated from code, compared against recorded values, and bound to a canonical receipt hash. Claim drift must fail closed.

---

## 7. SDA Concepts That Strengthen Weaver_OS

```text
REVIEW should become a governed deferred-proposal state.
Suspicion Budget can be modeled as governance debt accumulation.
Goal-level drift is a security object, not merely a content-classification problem.
```

Suggested future integration: a REVIEW turn emits a debt event with `debt_type`, `deferred_since`, `reconciliation_status`, and an expiration or escalation policy. Suspicion Budget threshold crossings can produce governance-debt events.

---

## 8. Do-Not-Import Boundary

The following layers are explicitly excluded from the SDA integration until separately justified and receipted:

```text
Loom / mythos layer
Hardware RTL
Lean / TLA+ / Z3 formal proof claims
Cathedral symbolic archive
Production authority language
```

Reason: importing these would overstate SDA's current status. SDA remains systematic, not formal; measured, not production-certified.

---

## 9. Registry Entry

```yaml
sda_integration:
  name: "SDA ↔ Weaver_OS Evidence-Spine Integration"
  status: "DRAFTED / PARTIALLY_IMPLEMENTED"
  maturity_ceiling: "L3"
  authority_impact_on_weaver_os: "none"
  production_authority: false
  formal_security_claim: false
  evidence_type: "engineering evidence only"
  receipt:
    verifier: "verify_claims.py"
    verifier_exit: 0
    claims_hash: "bf25ae33…"
    reproduced_claims: 6
    stable_against: "claims_receipt.json"
  verified_nucleus:
    - CIR
    - Constraint Drift
    - Suspicion Budget
    - max-risk aggregation
    - SWMR
    - beta failure surface
    - verify_claims.py receipt hash
  next_promotion_condition:
    - "Independent replay of verify_claims.py in a clean checkout."
  excluded_layers:
    - Loom / mythos layer
    - Hardware RTL
    - Lean / TLA+ / Z3 formal proof claims
    - Cathedral symbolic archive
    - Production authority language
```

---

## 10. Final Status

```text
SDA evidence spine integrated.
Receipt binding established.
Registry entry recorded.
L3 ceiling preserved.
External replay still required.
```

Final verdict: ACCEPT AS INTEGRATION ADDENDUM · NOT FORMAL PROOF · NOT PRODUCTION SECURITY CLAIM · READY FOR REPLAY-RECEIPT HARDENING.
