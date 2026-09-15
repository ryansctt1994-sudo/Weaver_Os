# TinyClaw Scaffold Test Posture

The scaffold test validates that the first-runtime governance wrapper files exist and retain fail-closed declarations.

It does not run TinyClaw, Strix, RosClaw, Docker, ROS2, or any external network service.

The stable CI entrypoint remains:

```text
pytest tests/triadic_controls -q
```
