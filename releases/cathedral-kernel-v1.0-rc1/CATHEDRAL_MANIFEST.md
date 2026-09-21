# Cathedral Kernel Manifest

Version: 1.0.0-rc1

Authority: RELEASE_CANDIDATE

## Purpose

Cathedral Kernel is a deterministic reference governance kernel for separating proposal, authority, evidence, witness legitimacy, veto, replay, receipt, and observability boundaries.

## Core Invariants

- CAPABILITY != AUTHORITY
- WITNESS_ATTESTATION != AUTHORITY
- SIGNED_ATTESTATION != AUTHORITY
- OBSERVABILITY != CORRECTNESS
- RECEIPT != PHYSICAL_VERIFICATION
- TLC_READY != TLC_PASSED
- NO_EXECUTION_WITHOUT_FRESH_AUTHORITY
- VETO_PREVENTS_COMMIT

## Generated Package

```text
cathedral-kernel-v1.0-rc1.zip
sha256: 5d283548cea999c18be699672a884a05c1b0c2a8cf4c101d01b0c31097f1e2ed
```

## Primary Modules in Generated Package

- schemas.py
- chronicle.py
- gate_engine.py
- authority_service.py
- lease_service.py
- resolver.py
- veto_service.py
- replay_engine.py
- witness.py
- signing.py
- quorum.py
- byzantine_quorum.py
- merkle.py
- receipt.py
- receipt_bundle.py
- dsse.py
- otel_projection.py
- hardware_veto.py
- bench_schema.py
- tlc_runner.py
- cli.py

## Formal / Hardware Artifacts in Generated Package

- formal/tla/CathedralKernel.tla
- formal/tla/CathedralKernel.cfg
- formal/tla/TLC_RESULTS.md
- hardware/rtl/lucifer_latch.v
- hardware/rtl/lucifer_latch_tb.v
- hardware/bench/BENCH_TEST_PLAN.md

## Claim Boundary

This release record preserves the artifact hash, validation transcript, and claim boundaries. It does not itself include the binary ZIP because the available GitHub connector supports repository file writes, not GitHub Release asset upload.
