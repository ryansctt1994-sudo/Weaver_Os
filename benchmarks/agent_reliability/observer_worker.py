"""Detached DRY-RUN observation process; stdio-only, no effect executor.

Not an OS security sandbox or independent witness. No filesystem/network APIs.
"""
from __future__ import annotations

import hashlib
import json
import sys


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def observe(document: dict) -> dict:
    if (set(document) != {"protocol", "events"}
            or document["protocol"] != "weaver-dry-observer-v0.3"):
        raise ValueError("invalid observer protocol")
    events = document["events"]
    if not isinstance(events, list) or len(events) > 1000:
        raise ValueError("invalid event count")
    previous = "0" * 64
    results = []
    for index, event in enumerate(events):
        if (not isinstance(event, dict)
                or set(event) != {"case", "attempt", "decision", "reason", "request"}
                or event["decision"] not in {"ALLOW", "DENY", "HALT"}
                or not isinstance(event["case"], str) or not isinstance(event["attempt"], int)
                or not isinstance(event["reason"], str) or not isinstance(event["request"], dict)):
            raise ValueError("malformed event")
        req = event["request"]
        if (set(req) != {"principal", "action", "resource", "payload", "nonce"}
                or not all(isinstance(x, str) for x in req.values())):
            raise ValueError("malformed request")
        effect = None
        if event["decision"] == "ALLOW":
            # Description only; no filesystem mutation, network or protected state.
            effect = {"kind": "WOULD_WRITE", "target_label": req["resource"],
                      "payload_sha256": hashlib.sha256(req["payload"].encode()).hexdigest()}
        record = {"sequence": index, "prev": previous, "event": event,
                  "would_effect": effect, "actual_effect": "NONE"}
        digest = hashlib.sha256(canonical(record)).hexdigest()
        results.append({**record, "hash": digest})
        previous = digest
    return {"protocol": "weaver-dry-observer-v0.3", "records": results, "head": previous,
            "real_commits": 0, "observer_classification": "SAME_HOST_PROCESS_NOT_INDEPENDENT"}


def main() -> int:
    try:
        document = json.loads(sys.stdin.read(2_000_001))
        output = observe(document)
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
