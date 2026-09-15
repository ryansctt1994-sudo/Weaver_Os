# RosClaw Transport Policy

Build: `B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME`

This file governs network transport endpoints for RosClaw simulation. It does not govern ROS topics. Topic permissions belong in `allowed_topics.yaml`.

## Approved simulation endpoints

```text
ws://localhost:9090
ws://ros2:9090
```

These match the rosbridge simulation posture documented in the RosClaw Docker compose flow.

## Denied posture

- public network exposure,
- production robots,
- unauthenticated remote rosbridge endpoints,
- physical actuation endpoints,
- arbitrary hostnames,
- arbitrary ports.

## Fail-closed rule

If the transport endpoint is not explicitly listed as approved simulation transport, the connection is denied.
