# Cathedral Kernel v1.0-rc1

Status: RELEASE_CANDIDATE

Maturity: P5 Release Candidate — DSSE / Observability-Projected Governance Kernel

This release record preserves the generated v1.0 release-candidate package metadata for Cathedral Kernel.

## Artifact

Generated archive: `cathedral-kernel-v1.0-rc1.zip`

SHA256:

```text
5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed
```

## Validation

```text
86 unit tests passed
CLI version passed
CLI demo passed
```

CLI version:

```text
python -m cathedral.cli version
→ 1.0.0-rc1
```

Demo receipt:

```text
PROPOSAL_CREATED
GATE_REJECTED: MISSING_AUTHORITY
AUTHORITY_GRANTED
EVIDENCE_ATTACHED
GATE_ADMITTED
LEASE_GRANTED
LEASE_REVALIDATED
VETO_TRIGGERED
EXECUTION_ABORTED
REPLAY_VERIFIED
WITNESS_REQUESTED
WITNESS_ATTESTED
SIGNED_WITNESS_ATTESTED
QUORUM_STATUS: QUORUM_MET
PROMOTION_STATUS: PROMOTABLE_E4
HARDWARE_VETO_SIMULATED
SIGNED_RECEIPT_BUNDLE_EXPORTED
DSSE_ENVELOPE_EXPORTED
OTEL_PROJECTION_EXPORTED
HARDWARE_BENCH_RESULT_SCHEMA_RECORDED
RECEIPT_EXPORTED
FINAL_STATUS: ABORTED_BY_HUMAN_VETO
```

## Included release-candidate components

```text
Stable public exports in cathedral.__init__
cathedral.version with __version__ = 1.0.0-rc1
cathedral-cli
CLI commands:
  version
  demo
  verify-chronicle
  manifest

CLAIM_BOUNDARY.md
STATUS.md
RECEIPT_VERSION_POLICY.md
CATHEDRAL_MANIFEST.md
RELEASE_FILE_MANIFEST.json
LICENSE
Updated README.md
pyproject.toml script entrypoint
Release ZIP SHA256 recorded
```

## Claim boundary

This release candidate proves behavior only where executable tests and receipts support the claim. It does not claim mechanically checked formal correctness, synthesized FPGA behavior, physical hardware latency, real fault-injection resilience, Byzantine safety under active collusion, hardware sovereignty, production executor containment, or Rekor/Sigstore submission.

See `CLAIM_BOUNDARY.md` in this release record.
