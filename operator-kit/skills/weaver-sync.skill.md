# Skill: Weaver Sync

## Purpose

Convert a conversation, screenshot batch, research note, code review, or external claim into a structured Weaver registry update proposal.

## Trigger

Use when the operator asks for synchronization, integration, must-keep extraction, registry update, or handoff preparation.

## Inputs

- Source material.
- Current registry or known canonical spine.
- Relevant freeze state, if available.

## Procedure

1. Extract new claims, artifacts, mechanisms, dependencies, risks, and proposed actions.
2. Separate facts, interpretations, assumptions, and speculation.
3. Identify conflict with existing invariants.
4. Identify whether each item is preservation-only, implementation-target, or promotion-candidate.
5. Produce a registry delta rather than silently rewriting canon.
6. Recommend next validation steps.

## Output schema

```yaml
sync_report:
  source_summary: string
  new_artifacts:
    - name: string
      type: code|doc|schema|workflow|policy|unknown
      status: preserved|implementation_target|promotion_candidate
      evidence_status: VERIFIED|LIKELY|SPECULATIVE|UNKNOWN
  new_claims:
    - claim: string
      evidence_status: VERIFIED|LIKELY|SPECULATIVE|UNKNOWN
      required_validation: string
  risks:
    - risk: string
      mitigation: string
  registry_delta:
    add:
      - string
    modify:
      - string
    reject:
      - string
  next_actions:
    - string
```

## Hard boundary

Do not promote artifacts based on rhetorical coherence, repeated mention, screenshots, or model confidence. Promotion requires receipt-grade evidence.