# Reality Gate v2

Status: E1 SPEC / CONTINUITY ARTIFACT

Reality Gate v2 upgrades the idea-to-execution boundary from an epistemic truth filter into a deterministic execution-scope check.

## Purpose

No Lane 1 idea, memory, symbolic artifact, dashboard signal, or model output may enter Lane 2 execution unless it passes the Reality Gate.

## Requirements

1. Truth: valid cryptographic signature or admitted truth label.
2. Evidence: schema compliance and required supporting evidence.
3. Proof: payload hash binding or proof reference.
4. Archive: trust ledger or archive entry exists.
5. Scope: authorized system, region, and task.
6. Duration: authority is within maximum allowed timeframe.
7. Consistency: no replay, no revoked key, no content drift.

## Weaver Scope Alignment

The following Weaver schema/runtime fields are treated as Reality Gate v2 constraints:

```text
allowed_scopes.systems
allowed_scopes.regions
allowed_scopes.tasks
max_authority_duration_sec
```

## Boundary Rule

The Reality Gate does not execute. It issues a passage or block.

```text
GatePassage -> may begin Lane 2 processing
GateBlock   -> explicit rejection with reason
```

## Non-Claims

Passing Reality Gate v2 is not the same as production execution. Execution still requires reducer acceptance, verifier evidence, ledger append, replay, and any required witness or hardware custody.
