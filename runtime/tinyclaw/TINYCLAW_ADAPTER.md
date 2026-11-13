# TinyClaw Adapter

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

TinyClaw is the operations runtime. It routes work; it does not authorize work.

## Scope

This adapter is declarative scaffolding only. It does not import or invoke TinyClaw runtime code.

## Required governed flow

```text
approved sender
  -> sender pairing policy
  -> TinyClaw queue intake
  -> QueueMessageReceipt
  -> AI Governance Runtime evaluate
  -> AI Governance Runtime enforce
  -> allow | block | escalate
  -> if allow: isolated agent workspace
  -> TeamHandoffReceipt / ToolCallReceipt / OutputHashReceipt
  -> replay verification
```

## Non-authority rule

TinyClaw must never be treated as an AuthorityKernel. Any request to run TinyClaw outside this wrapper remains outside governed status.

## Initial evidence posture

```text
repo: ryansctt1994-sudo/tinyclaw
commit: e912fd4d782e439238ce12c45f7ae924669388e9
observed_version: 0.0.6
evidence_status: E1_intake
promotion_gate: HOLD
```
