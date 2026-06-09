# Skill: Evidence Audit

## Purpose

Classify claims and artifacts according to the Weaver evidence discipline.

## Evidence labels

- VERIFIED: directly demonstrated, tested, observed, measured, or strongly sourced.
- LIKELY: supported by evidence but not fully verified.
- SPECULATIVE: plausible but unproven.
- UNKNOWN: insufficient information available.

## Procedure

1. List every material claim.
2. Identify the evidence offered for each claim.
3. Determine whether evidence is direct, indirect, testimonial, inferred, or absent.
4. Check whether implementation, execution, validation, and authority are being conflated.
5. Assign an evidence label.
6. Specify what would increase confidence.
7. Specify what would be required for promotion.

## Output schema

```yaml
evidence_audit:
  claims:
    - claim: string
      label: VERIFIED|LIKELY|SPECULATIVE|UNKNOWN
      evidence_present: string
      weakness: string
      promotion_requirement: string
  invalid_promotions:
    - item: string
      reason: string
  confidence_upgrades:
    - action: string
```

## Fail condition

If the source provides no reproducible evidence, mark the item as preservation-only or unknown. Do not infer validation from confidence or repetition.