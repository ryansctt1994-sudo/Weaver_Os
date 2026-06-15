# Verification Guide

## Purpose

This file explains how to verify the E3.1 Receipted Replay Package.

The goal is to allow a reviewer to confirm package integrity, reproduce the declared replay path, and check whether the claims register is consistent with the available evidence.

## Scope

This verification guide covers package integrity, manifest integrity, evidence-hash integrity, replay report review, claim-to-evidence traceability, and basic environment confirmation.

It does not claim independent replication, adversarial reproduction, external audit, operational authority, or production authority.

## Verification sequence

1. Read `AUDIT_PACKAGE.md`, `README.md`, and `LIMITATIONS_AND_NONCLAIMS.md`.
2. Check files listed in `SHA256SUMS.txt` once hashes are generated.
3. Confirm environment assumptions in `ENVIRONMENT_MANIFEST.md`.
4. Review `E3_1_RECEIPTED_REPLAY_PACKAGE.md`, `REPLAY_REPORT.md`, and `REPRODUCTION_INSTRUCTIONS.md`.
5. Review `EVIDENCE_MANIFEST.md` and `CLAIMS_AND_EVIDENCE.md`.
6. Review `CLAIM_TRACEABILITY_MATRIX.md`.
7. Review `WITNESS_ATTESTATIONS.md` and `CHAIN_INTEGRITY_REPORT.md`.
8. Review `FAILURE_AND_COUNTEREXAMPLE_LOG.md` and `LIMITATIONS_AND_NONCLAIMS.md`.
9. Record a finding using `REVIEWER_CONCLUSION_TEMPLATE.md`.

## Suggested outcomes

- Consistent
- Locally supported
- Partially supported
- Requires more evidence
- Not supported
- Inconclusive

## Verification note

A reviewer should not upgrade the evidence level based on narrative strength alone. Evidence level must follow the strongest verifiable artifact currently available.
