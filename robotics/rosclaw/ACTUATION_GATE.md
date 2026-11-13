# RosClaw Actuation Gate

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

The actuation gate prevents language-model output from becoming physical motion.

## Rule

```text
simulation commands may be evaluated;
physical commands are denied by default.
```

## Fail-closed checks

- Unknown topic: deny.
- Unknown service: deny.
- Unknown action: deny.
- Missing robot command receipt: deny.
- Missing simulation authority: deny.
- Missing estop binding: deny.
- Missing workspace limits: deny.
- Any authority lease status other than active/reinstated within scope: deny.

## Allowed first-build behavior

Only simulation-only ROS messages listed in `allowed_topics.yaml` may be considered by future code.

This file is declarative and non-executing.
