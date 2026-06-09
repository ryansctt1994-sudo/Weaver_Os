# Weaver Operator Workspace Skeleton

```text
WEAVER_OPERATOR_WORKSPACE/
  ABOUT-ME/
    ryan-profile.md
    operating-style.md
    project-goals.md

  REFERENCE/
    constitution/
      METACONSTITUTION.md
      CONSTITUTION.md
      EVIDENCE_PROMOTION_LADDER.md
      FOUR_WAY_SEPARATION.md
      AUTHORITY_MODEL.md
      SEMANTIC_SKEW_FAILURES.md

    registries/
      MUST_KEEP_REGISTRY.md
      CVP_FREEZE_2026_06_06.md
      artifact_inventory.md
      receipts_index.md

    architecture/
      CEK.md
      Chronicle.md
      WeaverKernel.md
      Lumen.md
      SECA.md
      Ouroboros.md

  SKILLS/
    weaver-sync.skill.md
    evidence-audit.skill.md
    handoff-generator.skill.md
    artifact-classifier.skill.md
    claim-extractor.skill.md
    implementation-plan.skill.md
    rebuttal-composer.skill.md
    receipt-check.skill.md

  OUTPUTS/
    handoffs/
    audits/
    receipts/
    summaries/
    implementation-plans/
    rebuttals/

  TEMPLATES/
    final-handoff-template.md
    evidence-report-template.md
    must-keep-registry-template.md
    claim-status-template.md
    pro-rebuttal-template.md
```

## Workspace rule

Every operator run should write to `OUTPUTS/` first. Registry mutation requires review, provenance, and a receipt path.

## Minimum run record

Each run should preserve:

- Input source or conversation reference.
- Skill used.
- Output path.
- Claims extracted.
- Evidence status.
- Promotion recommendation.
- Reviewer decision.

## Non-goal

This workspace does not grant authority to any generated artifact. It only improves continuity, repeatability, and reviewability.