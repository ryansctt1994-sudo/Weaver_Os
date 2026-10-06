# Cathedral Kernel v1.0-rc1 Validation Transcript

## Test Suite

```text
86 unit tests passed
```

## CLI Version

```text
python -m cathedral.cli version
1.0.0-rc1
```

## CLI Demo

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

## Runtime Note

A spreadsheet runtime warmup warning appeared during Python startup in the build environment. It was unrelated to the package under test. Tests, CLI version, and CLI demo completed successfully.

## TLC Status

```text
Status: TOOL_NOT_AVAILABLE
Command: tlc CathedralKernel.tla -config CathedralKernel.cfg
Return code: 127
```

No mechanically checked formal correctness is claimed.
