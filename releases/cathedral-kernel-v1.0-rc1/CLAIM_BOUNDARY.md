# Cathedral Kernel Claim Boundary

Version: 1.0.0-rc1

## Prime Boundary

Capability does not create authority.
Witness attestation does not create authority.
Evidence strengthens legitimacy but does not grant execution capability.
Observability exports describe behavior but do not prove correctness.

## Proven in Code

The generated package includes tests covering:

- authority separation
- gate admissibility
- resolver transition constraints
- replay receipts
- veto abort behavior
- authority freshness through execution leases
- witness replay and witness quorum evaluation
- signed witness attestations
- Merkle roots and inclusion proofs
- signed receipt bundles
- DSSE-style receipt envelopes
- OpenTelemetry-compatible projection
- hardware veto simulation
- hardware bench result schema
- PBFT-style quorum policy checks

## Recorded but Not Passed

TLC model checking was attempted where the package was built. In that build environment, TLC was not available.

Status: TOOL_NOT_AVAILABLE

No mechanically checked formal correctness is claimed unless `formal/tla/TLC_RESULTS.md` records `Status: PASSED`.

## Artifacted but Not Physically Verified

- RTL veto latch
- RTL testbench
- hardware bench plan
- hardware bench result schema

No synthesized FPGA behavior, physical latency, or real fault-injection resilience is claimed.

## Projected but Not Live

OpenTelemetry-compatible logs, metrics, and spans are generated as export-shaped objects. No live collector integration is claimed.

## Unproven

- mechanically checked formal correctness
- synthesized FPGA behavior
- physical hardware latency
- real fault-injection resilience
- Byzantine safety under active collusion
- hardware sovereignty
- production executor containment
- Rekor/Sigstore submission
