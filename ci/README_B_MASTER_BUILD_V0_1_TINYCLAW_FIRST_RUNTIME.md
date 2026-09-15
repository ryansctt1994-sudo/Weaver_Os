# CI Note: B_MASTER_BUILD_V0_1_TINYCLAW_FIRST_RUNTIME

This package intentionally preserves the existing `triadic-controls CI` entrypoint.

The current scaffold validation is located at:

```text
tests/triadic_controls/test_tinyclaw_first_runtime_scaffold.py
```

It validates only declarative files and does not invoke TinyClaw, Strix, RosClaw, Docker, ROS2, or external network targets.

Future runtime execution requires separate receipts and promotion-gate updates.
