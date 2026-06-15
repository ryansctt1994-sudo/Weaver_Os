# E3.1 Receipted Replay Package

Revision: 2026-06 Final Consolidated Freeze
Evidence Level: E3.1 Target
Purpose: Reviewer-executable replay package
Status: Internal replay evidence only
External authority: Not earned

## Objective

This package demonstrates the current receipted replay posture of the Weaver Covenant / DEEK / Canon-OS ecosystem.

It is intended to let an external reviewer examine whether replay is reproducible, properly receipted, correctly bounded, and honestly represented.

## Claim

The system supports receipted replay at the current evidence level.

## Claim boundary

This claim does not imply independent replay, independent replication, adversarial reproduction, external audit, operational authority, or production authority.

## Replay categories

Actions must be classified as one of:

- Replay-safe
- Replay-simulated
- Replay-prohibited
- Compensatable
- Unknown

Unknown actions are non-authoritative until classified.

## Reviewer flow

1. Verify package hashes using `SHA256SUMS.txt`.
2. Confirm environment assumptions in `ENVIRONMENT_MANIFEST.md`.
3. Follow `REPRODUCTION_INSTRUCTIONS.md`.
4. Compare observed outputs against `REPLAY_REPORT.md`.
5. Confirm evidence items in `EVIDENCE_MANIFEST.md`.
6. Verify claim mappings in `CLAIM_TRACEABILITY_MATRIX.md`.
7. Inspect witness attestations and chain integrity.
8. Confirm failures and limitations are preserved.
9. Record an outcome using `REVIEWER_CONCLUSION_TEMPLATE.md`.

## Final note

This package is intentionally narrow. It supports a receipted replay review, not complete system authority.
