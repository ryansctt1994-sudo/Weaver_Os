# RosClaw Estop Policy

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

Emergency stop must remain available outside AI deliberation.

## Rule

```text
/estop bypasses AI and sends zero-motion intent in simulation.
```

## Required behavior for future implementation

- `/estop` must never require model approval.
- `/estop` must be logged with a RobotCommandReceipt.
- `/estop` must not be blocked by ordinary planning gates.
- `/estop` must not authorize any follow-up motion.
- Missing estop binding blocks any future physical promotion.

## Current posture

```text
simulation_estop: specified
physical_estop: not validated
physical_actuation: blocked_by_default
```
