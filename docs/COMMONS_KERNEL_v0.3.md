# Commons Kernel v0.3 — Executable Adversarial Slice

Status: implementation candidate, not validated society.

Invariant under test:

> Unauthorized promotion is rejected without mutating protected state.

Formal authority is granted only by an explicit, active grant matching subject,
action, and target. Nesting, federation size, routing position, coordination
role, infrastructure control, reputation, copying/forking, or predecessor
history do not create authority.

## CK-ADV-001

This branch implements the first executable tranche:

- authorized narrow grant -> ACCEPT
- larger-group / federation authority -> REJECT
- routing-control escalation -> REJECT
- coordinator-to-command escalation -> REJECT
- delegation beyond scope -> REJECT
- fork/copy inheritance -> REJECT
- infrastructure-to-authority escalation -> REJECT
- reputation-to-authority escalation -> REJECT
- target-scope expansion -> REJECT
- expired grant -> REJECT
- revoked grant -> REJECT
- dissolved-cell inheritance -> REJECT
- every rejection -> protected-state hash unchanged

Run:

```bash
pytest -q tests/test_commons_kernel_adv001.py
```

## Evidence boundary

Passing tests establish only local executable behavior of this reference slice.
They do not establish social legitimacy, real-world resilience, CK-ADV-002
hidden-throne resistance, CK-HUM-001 human comprehension, production readiness,
or independent reproduction.
