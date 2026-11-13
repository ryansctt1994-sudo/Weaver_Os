# TinyClaw Security Hardening

This checklist records hardening requirements before any governed TinyClaw execution.

## Current posture

```text
runtime_invocation: blocked
standalone_authority: denied
promotion_gate: HOLD
```

## Required controls

- Sender pairing must precede queue acceptance.
- Every queue message must produce a QueueMessageReceipt.
- Blocked requests must never reach agent workspaces.
- Agent workspace paths must be isolated per agent/team.
- Runtime flags that bypass approvals, sandboxing, or provider permissions are prohibited unless explicitly wrapped and receipted.
- Suspected dangerous flags remain checklist items until direct file evidence confirms or clears them.
- TinyOffice settings mutation must be treated as privileged configuration change.
- Channel tokens must never be committed.
- Logs must not contain secrets.

## Fail-closed triggers

- unknown sender reaches an agent,
- queue receipt missing,
- team handoff receipt missing,
- workspace isolation failure,
- critical/high Strix finding open,
- authority lease is challenged, suspended, restricted outside scope, or revoked.
