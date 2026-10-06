#!/usr/bin/env python3
"""Deterministic fixture emitter for runtime-state contract tests.

This is test machinery, not the Weaver runtime.
"""

import json

print(
    json.dumps(
        {
            "schema": "weaver-runtime-state-1",
            "runtime_id": "fixture-runtime",
            "source_binding": {
                "kind": "git_commit",
                "value": "1" * 40,
            },
            "replay_input_digest": "2" * 64,
            "state": {
                "protected": {"counter": 1},
                "used": ["N1"],
            },
        },
        sort_keys=True,
    )
)
