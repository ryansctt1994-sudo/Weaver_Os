"""Deterministic structured tracing for Weaver activation correspondence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

TRACE_SCHEMA_VERSION = "weaver-activation-trace-2"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class ActivationTraceRecorder:
    """Collect canonical, append-only activation transition observations."""

    def __init__(self) -> None:
        self._events: list[dict[str, object]] = []

    def emit(self, action: str, request_id: str, **fields: object) -> None:
        event: dict[str, object] = {
            "schema_version": TRACE_SCHEMA_VERSION,
            "seq": len(self._events),
            "action": action,
            "request_id": request_id,
            **fields,
        }
        _canonical_json(event)
        self._events.append(copy.deepcopy(event))

    @property
    def events(self) -> tuple[dict[str, object], ...]:
        return tuple(copy.deepcopy(event) for event in self._events)

    def canonical_ndjson(self) -> bytes:
        return b"".join(_canonical_json(event) + b"\n" for event in self._events)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_ndjson()).hexdigest()

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.canonical_ndjson())
