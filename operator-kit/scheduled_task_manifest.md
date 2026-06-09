# Scheduled Task Manifest

## Purpose

Define recurring operator runs for continuity, drift control, and evidence hygiene.

## Daily tasks

### Daily registry intake

Cadence: daily.

Input: latest conversations, notes, commits, or artifacts.

Output: `OUTPUTS/summaries/YYYY-MM-DD-registry-intake.md`.

Promotion: none by default.

### Daily evidence triage

Cadence: daily.

Input: newly generated claims and artifacts.

Output: `OUTPUTS/audits/YYYY-MM-DD-evidence-triage.md`.

Promotion: only after receipt check.

## Weekly tasks

### Weekly artifact audit

Cadence: weekly.

Input: current registry and new outputs.

Output: `OUTPUTS/audits/YYYY-WW-artifact-audit.md`.

Checks:

- stale artifacts
- unsupported claims
- duplicate concepts
- implementation gaps
- promotion candidates

### Weekly handoff refresh

Cadence: weekly.

Input: canonical registry, latest receipts, open risks.

Output: `OUTPUTS/handoffs/YYYY-WW-fresh-session-handoff.md`.

## Conditional tasks

### Receipt promotion watch

Condition: an artifact gains reproduction steps, validation output, hash anchor, and witness path.

Action: run receipt check and propose promotion.

### Semantic skew watch

Condition: a new artifact changes terminology, authority boundaries, or canonical invariants.

Action: run evidence audit and registry sync before adoption.

## Rule

Scheduled output is not authority. It is a review queue.