# TinyOffice Operator Console

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

TinyOffice may observe queue state, logs, agents, teams, tasks, and settings, but it must not become an authority surface.

## Allowed posture

- read-only operational visibility,
- operator review of queued work,
- inspection of receipts and replay reports,
- manual review handoff when policy returns `escalate`.

## Denied posture

- bypassing sender pairing,
- mutating settings without a configuration receipt,
- launching agents without AI Governance Runtime evaluation,
- approving physical actuation,
- promoting runtime authority.

## Required future receipt

Settings changes must produce a `ConsoleConfigReceipt` with actor, setting path, previous hash, new hash, authority lease, and receipt hash.
