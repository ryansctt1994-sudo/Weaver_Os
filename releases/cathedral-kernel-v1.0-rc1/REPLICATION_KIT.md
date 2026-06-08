# Cathedral Kernel v1.0-rc1 Replication Kit

Status: REPLICATION_READY_METADATA

Authority: L1_SPECIFIED / L2_IMPLEMENTED

This replication kit defines the minimum independent replay procedure required to attempt promotion beyond the current L2 implemented release-record status.

## Prime Rule

Replication may strengthen legitimacy, but it does not create authority.

A successful local replay is not global authority. A failed replay blocks promotion until investigated.

## Release Artifact Under Test

```text
cathedral-kernel-v1.0-rc1.zip
sha256: 5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed
```

The binary ZIP was generated outside this repository and is not attached here as a GitHub Release asset. This repository records its hash, validation transcript, and claim boundary.

## Replication Preconditions

An independent replicator must obtain the archive and verify:

```bash
sha256sum cathedral-kernel-v1.0-rc1.zip
```

Expected:

```text
5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed  cathedral-kernel-v1.0-rc1.zip
```

## Minimal Replay Procedure

```bash
unzip cathedral-kernel-v1.0-rc1.zip
cd cathedral-kernel-v1.0-rc1
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m cathedral.cli version
PYTHONPATH=src python -m cathedral.cli demo
PYTHONPATH=src python -m cathedral.cli manifest . > replication_manifest.json
```

## Expected Results

```text
86 unit tests passed
cathedral.cli version -> 1.0.0-rc1
cathedral.cli demo emits FINAL_STATUS: ABORTED_BY_HUMAN_VETO
```

The demo should include:

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

## Replication Receipt Template

Independent replicators should record:

```yaml
replication_receipt:
  artifact: cathedral-kernel-v1.0-rc1.zip
  artifact_sha256_observed: ""
  artifact_sha256_expected: "5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed"
  environment:
    os: ""
    python_version: ""
    shell: ""
  commands:
    - command: "PYTHONPATH=src python -m unittest discover -s tests -v"
      exit_code: null
      observed_result: ""
    - command: "PYTHONPATH=src python -m cathedral.cli version"
      exit_code: null
      observed_result: ""
    - command: "PYTHONPATH=src python -m cathedral.cli demo"
      exit_code: null
      observed_result: ""
  expected_demo_terminal_status: "FINAL_STATUS: ABORTED_BY_HUMAN_VETO"
  tlc_status_observed: ""
  notes: ""
  reviewer: ""
  timestamp_utc: ""
```

## Promotion Rules

- Matching hash + passing tests + matching CLI demo may support L3_LOCALLY_DEMONSTRATED for the release package in the replicator environment.
- Independent replicator receipt may support L4_INDEPENDENTLY_REPLICATED only if the replay is performed outside the original build context and the receipt is preserved.
- TLC remains unpassed unless the replicator runs TLC and records `Status: PASSED`.
- Hardware remains unverified unless physical bench measurements are captured and Chronicle-sealed.

## Failure Handling

Any mismatch must be recorded as a rejection receipt, not overwritten.

Failure classes:

```text
HASH_MISMATCH
TEST_FAILURE
CLI_VERSION_MISMATCH
DEMO_RECEIPT_MISMATCH
TLC_UNAVAILABLE
TLC_FAILURE
ENVIRONMENTAL_DEPENDENCY_FAILURE
```

## Current Boundary

This kit defines a replay path. It does not itself perform independent replication.
