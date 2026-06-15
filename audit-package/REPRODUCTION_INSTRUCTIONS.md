# Reproduction Instructions

## Purpose

This document tells a reviewer how to reproduce the E3.1 replay package and verify the declared evidence.

## Scope

These instructions support reviewer execution of the receipted replay path only.

They do not establish independent replication, adversarial reproduction, external audit, operational authority, or production authority.

## Workflow

1. Verify package integrity against `SHA256SUMS.txt` once hashes are generated.
2. Confirm the environment in `ENVIRONMENT_MANIFEST.md`.
3. Read `AUDIT_PACKAGE.md`, `README.md`, and `LIMITATIONS_AND_NONCLAIMS.md`.
4. Review `CLAIMS_AND_EVIDENCE.md` and `CLAIM_TRACEABILITY_MATRIX.md`.
5. Review `E3_1_RECEIPTED_REPLAY_PACKAGE.md`, `REPLAY_REPORT.md`, and `VERIFICATION_REPORT.md`.
6. Inspect `EVIDENCE_MANIFEST.md`, `CHAIN_INTEGRITY_REPORT.md`, `WITNESS_ATTESTATIONS.md`, and `FAILURE_AND_COUNTEREXAMPLE_LOG.md`.
7. Record the result in `REVIEWER_CONCLUSION_TEMPLATE.md`.

## Failure conditions

Stop and mark the package as not fully reviewable if any of the following occur:

- Missing file
- Hash mismatch
- Unreadable manifest
- Replay claim without support
- Authority claim exceeding evidence
- Traceability gap with no explanation
- Witness independence left undefined
- Failure logs omitted or erased

## Completion condition

Reproduction is complete when the reviewer has verified package integrity, reviewed the replay claim, inspected traceability, confirmed limits, and recorded a conclusion.
