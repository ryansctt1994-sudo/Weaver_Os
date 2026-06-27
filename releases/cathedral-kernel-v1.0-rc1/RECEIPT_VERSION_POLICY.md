# Receipt Version Policy

## Current Receipt Version

1.0.0-rc1 emits receipt-compatible structures inherited from v0.9:

- JSON receipt payloads
- signed receipt bundles
- DSSE-style envelopes
- Merkle roots and inclusion proofs
- witness attestations and quorum results

## Compatibility Rule

Patch releases must not remove required receipt fields.

Minor releases may add optional fields.

Major releases may alter required fields only with a migration document.

## Required Claim Boundary

A receipt proves only what the included artifacts can verify.

A receipt does not prove:

- physical hardware behavior
- formal correctness
- Byzantine safety under active collusion
- production containment

unless corresponding evidence is included and verified.
