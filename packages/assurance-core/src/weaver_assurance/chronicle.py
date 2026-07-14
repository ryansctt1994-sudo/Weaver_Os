"""Fail-closed append-only Chronicle with checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .canonical import canonical_json, sha256_json


GENESIS = "0" * 64


@dataclass(frozen=True)
class ChronicleReport:
    valid: bool
    count: int
    head: str
    reason: str


def _merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return GENESIS
    layer = [bytes.fromhex(value) for value in hashes]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()


class Chronicle:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._thread_lock = threading.Lock()

    @staticmethod
    def _hash_entry(entry: dict[str, Any]) -> str:
        body = dict(entry)
        body.pop("hash", None)
        return sha256_json(body)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Chronicle JSON at line {number}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"Chronicle line {number} is not an object")
                entries.append(value)
        return entries

    @classmethod
    def verify_entries(cls, entries: list[dict[str, Any]]) -> ChronicleReport:
        previous = GENESIS
        for index, entry in enumerate(entries):
            if entry.get("index") != index:
                return ChronicleReport(False, index, previous, "INDEX_MISMATCH")
            if entry.get("prev_hash") != previous:
                return ChronicleReport(False, index, previous, "PREV_HASH_MISMATCH")
            claimed = entry.get("hash")
            if not isinstance(claimed, str) or claimed != cls._hash_entry(entry):
                return ChronicleReport(False, index, previous, "ENTRY_HASH_MISMATCH")
            previous = claimed
        return ChronicleReport(True, len(entries), previous, "VALID")

    def verify(self) -> ChronicleReport:
        try:
            return self.verify_entries(self._read_unlocked())
        except (OSError, ValueError, TypeError):
            return ChronicleReport(False, 0, GENESIS, "READ_ERROR")

    def append(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        timestamp_ns: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not event_type:
            raise ValueError("event_type must be non-empty")
        with self._thread_lock:
            lock_path = self.path.with_suffix(self.path.suffix + ".lock")
            with lock_path.open("a+b") as lock_handle:
                self._lock_file(lock_handle)
                try:
                    entries = self._read_unlocked()
                    report = self.verify_entries(entries)
                    if not report.valid:
                        raise ValueError(f"refusing append to invalid Chronicle: {report.reason}")
                    entry = {
                        "version": "weaver.chronicle.entry.v1",
                        "index": report.count,
                        "timestamp_ns": int(time.time_ns() if timestamp_ns is None else timestamp_ns),
                        "event_type": event_type,
                        "data": data,
                        "metadata": metadata or {},
                        "prev_hash": report.head,
                    }
                    entry["hash"] = self._hash_entry(entry)
                    encoded = canonical_json(entry) + b"\n"
                    with self.path.open("ab") as output:
                        output.write(encoded)
                        output.flush()
                        os.fsync(output.fileno())
                    return entry
                finally:
                    self._unlock_file(lock_handle)

    def checkpoint(self) -> dict[str, Any]:
        entries = self._read_unlocked()
        report = self.verify_entries(entries)
        if not report.valid:
            raise ValueError(f"cannot checkpoint invalid Chronicle: {report.reason}")
        return {
            "version": "weaver.chronicle.checkpoint.v1",
            "count": report.count,
            "head": report.head,
            "merkle_root": _merkle_root([entry["hash"] for entry in entries]),
        }

    def verify_checkpoint(self, checkpoint: dict[str, Any]) -> bool:
        try:
            return self.checkpoint() == checkpoint
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def entries(self) -> Iterator[dict[str, Any]]:
        yield from self._read_unlocked()

    @staticmethod
    def _lock_file(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _unlock_file(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

