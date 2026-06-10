# Boundary Integrity Demo: The Throne Remains Empty

This dependency-free demo illustrates the Validation Algebra boundary rules for the Delta-717 / Cathedral-OS / Weaver architecture.

Status: `ACCEPTED_AS_DEMO_DESIGN` until executed and receipted.
Authority: `TEST_DESIGN_ONLY`.
Authority weight: `0`.

The demo performs local predicate validation only. Full JSON Schema validation remains in the PR-001 -> PR-005 stack.

## What it demonstrates

1. Clean ordinary proposals can commit without minting authority.
2. Requested authority movement inside a proposal is rejected for ordinary transitions.
3. A tampered record body fails self-integrity hashing before it can act as evidence.
4. A CVP promotion request without witness reports is deferred.

## Run locally

```bash
chmod +x demo/run_demo.sh
bash demo/run_demo.sh
```

## Generate a local stdout receipt

```bash
mkdir -p receipts/demo
bash demo/run_demo.sh | tee receipts/demo/boundary_integrity_demo_v0_1_stdout.txt
sha256sum receipts/demo/boundary_integrity_demo_v0_1_stdout.txt
```

## Expected verdict sequence

```text
CASE 01: ACCEPT
CASE 02: REJECT
CASE 03: REJECT
CASE 04: DEFER
```

## Boundary statement

```text
Proposal != Authority
Narration != Evidence
Evidence Growth != Authority Growth
The Throne Remains Empty
```
