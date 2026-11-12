# WF-001 — ZOREL Typed-Action Bridge

**Status:** Review-only draft. DO NOT MERGE.  
**Evidence classification:** E2 / W0 / O0. V008 HOLD unchanged.  
**Base commit:** `90e345b1fc65eec6b197dda74cd509718ad0a6a7` (Weaver_Os PR #129).

## Objective

Convert one narrowly defined ZOREL-style `ActionOp` into an immutable Weaver `Proposal`, while preserving Weaver's authority boundary.

The adapter never creates a grant, signs a proposal, accesses a ledger, or executes an operation.

## Source pins

| Repository | Commit | Role |
|------------|--------|------|
| Weaver_Os | `90e345b1fc65eec6b197dda74cd509718ad0a6a7` | Base; existing `Proposal` and WX-CJSON-1 contracts |
| Delta-717 | `c0a84e44967f9206fecc601acd370b5d7642fa0a` | Observer-only fixture source (not imported at runtime) |
| zorel-kernel | `abd777e43906cd7bacbd210a5975665730446d2f` | ActionOp shape reference |

## Input contract (WF-ACTION-1)

Exactly these fields:

```json
{
  "schema": "WF-ACTION-1",
  "proposal_id": "wf001-demo-001",
  "policy_version": "policy-v1",
  "action_op": {
    "op_type": "WRITE_KEY",
    "actor": "agent-a",
    "target": "status",
    "payload": {"value": "ready"},
    "authority_required": "standard"
  }
}
```

`authority_required` is a declaration. Only `"standard"` is accepted. Actual permission remains Weaver's signed-grant mechanism.

## Output contract

A `weaver_contracts.gate.Proposal`:

```json
{
  "proposal_id": "wf001-demo-001",
  "actor_id": "agent-a",
  "action": "WRITE_KEY",
  "policy_version": "policy-v1",
  "payload": {"key": "status", "value": "ready"}
}
```

The output must pass Weaver's existing `Proposal` validation and `WX-CJSON-1` canonicalization.

## Implementation boundaries

| Component | Modified |
|-----------|----------|
| `packages/fusion/weaver_fusion/` | Yes (new) |
| `tests/fusion/` | Yes (new) |
| `docs/fusion/` | Yes (new) |
| `weaver_runtime.owner_service` | No |
| `weaver_runtime.protected_write` | No |
| `weaver_runtime.gate` | No |
| Signed-grant verification | No |
| Receipt and ledger semantics | No |

## Negative controls

The tests under `tests/fusion/` cover:

- Unsupported action types rejected.
- Extra or missing input fields rejected.
- Non-string identities and malformed values rejected.
- Mutable input dictionaries cannot change a constructed proposal.
- Equivalent encodings produce identical canonical proposal bytes.
- Changing actor, target, value, or policy version changes the canonical digest.
- No adapter output can substitute for a valid signed grant.
- A Delta-717-style `APPROVED` assessment cannot cause execution.
- Unsupported authority declarations rejected rather than elevated.

## Non-claims

- This adapter does not grant execution authority.
- A Delta-717 assessment is not an authorization decision.
- Existing V008 isolation, recovery, and authorization tests are unchanged.
- Evidence classification and operational authority are not elevated.

## Review

Human review of the exact head is required before any merge decision. This remains a draft.
