# WEAVER AI OPERATOR KIT v0.1

Status: Preservation artifact / operator workflow scaffold.

Promotion rule: inclusion here does not canonize or verify any claim. Only replayable receipts, provenance, validation, and independent witness checks promote artifacts.

## Objective

Convert ad-hoc AI chat sessions into bounded operator runs that can read context, execute reusable skills, produce artifacts, and update project registries only when evidence supports promotion.

## Core design

The kit treats AI systems as operator environments rather than temporary chat boxes. Each run should have:

1. A persistent workspace.
2. Explicit reference material.
3. Reusable skill files.
4. Output locations.
5. Templates for repeatable artifacts.
6. Evidence status labels.
7. Human review before registry mutation.

## Folder model

```text
WEAVER_OPERATOR_WORKSPACE/
  ABOUT-ME/
  REFERENCE/
  SKILLS/
  OUTPUTS/
  TEMPLATES/
```

## Execution invariant

No proposal, cognition, coherence, optimization result, benchmark score, actor, consensus, or runtime mutation becomes authority without provenance, admissibility, verification, replay, constraints, and receipt sealing.

## Included files

- `workspace_skeleton.md` — local-first folder structure.
- `skills/weaver-sync.skill.md` — conversation-to-registry synchronization.
- `skills/evidence-audit.skill.md` — claim classification and verification review.
- `skills/handoff-generator.skill.md` — fresh-session handoff production.
- `skills/receipt-check.skill.md` — promotion readiness check.
- `local_vs_cloud_routing_policy.md` — private/local versus cloud execution routing.
- `scheduled_task_manifest.md` — recurring operator task definitions.
- `daily_operator_loop.md` — daily run procedure.
- `weekly_audit_loop.md` — weekly audit procedure.

## Evidence status

This is a design and workflow scaffold. It is not yet validated as an implemented automation system. Current status: LIKELY USEFUL / NOT PROMOTED.