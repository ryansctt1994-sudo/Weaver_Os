# Skill: Receipt Check

## Purpose

Evaluate whether an artifact is eligible for promotion under the Weaver receipt discipline.

## Required checks

- Provenance is known.
- Inputs are identified.
- Output artifact is stable and addressable.
- Execution path is documented.
- Reproduction steps exist.
- Validation result exists.
- Hash or equivalent integrity anchor exists.
- Witness or independent review path exists.
- Authority boundary is stated.

## Output schema

```yaml
receipt_check:
  artifact: string
  eligible_for_promotion: true|false
  missing_requirements:
    - string
  evidence_status: VERIFIED|LIKELY|SPECULATIVE|UNKNOWN
  recommended_next_action: string
```

## Rule

A useful artifact can remain useful without being promoted. Promotion requires receipt-grade evidence, not usefulness alone.