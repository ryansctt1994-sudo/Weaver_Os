# Strix Report Mapping

This file maps Strix output into governed evidence. It is declarative and does not execute Strix.

## Mapping

```text
Strix run -> SecurityScanReceipt
Strix finding -> VulnerabilityFindingReceipt
critical/high finding -> ChallengeGate docket
fix evidence -> FixVerificationReceipt
re-scan pass -> ReinstatementGate candidate
```

## Severity effect

```text
critical -> authority status: suspended
high     -> authority status: challenged or restricted
medium   -> promotion gate remains HOLD pending review
low      -> tracked, does not promote
info     -> tracked only
```

## Non-authority rule

A clean Strix scan is not authority. It is evidence for PromotionGate review.
