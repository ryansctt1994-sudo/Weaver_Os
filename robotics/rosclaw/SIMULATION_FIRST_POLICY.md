# RosClaw Simulation-First Policy

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

RosClaw is the physical adapter lane. It remains simulation-only in this build.

## Default posture

```text
PHYSICAL_ACTUATION: BLOCKED_BY_DEFAULT
SIMULATION: allowed only through approved transport and topic policies
PROMOTION_GATE: HOLD
```

## Required physical-actuation prerequisites

Physical actuation is not authorized unless all of the following exist:

1. human approval,
2. simulation pass receipt,
3. Strix scan receipt with no unresolved critical/high findings,
4. RobotCommandReceipt,
5. workspace limits,
6. velocity limits,
7. estop verification,
8. physical-world authority scope,
9. explicit promotion receipt.

## Non-execution posture

This policy does not invoke RosClaw, ROS2, rosbridge, Gazebo, OpenClaw, or any robot.
