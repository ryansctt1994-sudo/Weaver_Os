"""Registry sequence stores (runtime domain), implementing
``weaver_contracts.registry_sequence.RegistrySequenceStoreProtocol``.

``InMemoryRegistrySequenceStore`` is for tests and single-process simulation: its mark is
lost on restart, so it does not protect against a rollback across restarts.

``SQLiteRegistrySequenceStore`` persists the mark. ``advance`` reads and writes inside one
``BEGIN IMMEDIATE`` transaction, so concurrent callers on separate connections are
serialized by SQLite and at most one of two conflicting registries at the same sequence
is accepted. Scope is one SQLite file on a local file system.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from weaver_contracts.registry_sequence import RegistrySequenceStoreProtocol, decide


class InMemoryRegistrySequenceStore(RegistrySequenceStoreProtocol):
    def __init__(self) -> None:
        self._marks: dict[str, tuple[int, str]] = {}
        self._lock = threading.Lock()

    def advance(self, registry_id: str, sequence: int, digest: str) -> str | None:
        with self._lock:
            refusal = decide(self._marks.get(registry_id), sequence, digest)
            if refusal is None:
                self._marks[registry_id] = (sequence, digest)
            return refusal


class SQLiteRegistrySequenceStore(RegistrySequenceStoreProtocol):
    def __init__(self, db_path: str | Path, *, busy_timeout_ms: int = 5000) -> None:
        self.db_path = str(db_path)
        self._busy_timeout_ms = busy_timeout_ms
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registry_sequence (
                    registry_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL,
                    digest TEXT NOT NULL
                )
                """
            )
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute(f"PRAGMA busy_timeout={int(self._busy_timeout_ms)};")
        return conn

    def advance(self, registry_id: str, sequence: int, digest: str) -> str | None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT sequence, digest FROM registry_sequence WHERE registry_id = ?",
                (registry_id,),
            ).fetchone()
            current = (int(row[0]), str(row[1])) if row is not None else None
            refusal = decide(current, sequence, digest)
            if refusal is None:
                conn.execute(
                    """
                    INSERT INTO registry_sequence (registry_id, sequence, digest)
                    VALUES (?, ?, ?)
                    ON CONFLICT(registry_id) DO UPDATE
                    SET sequence = excluded.sequence, digest = excluded.digest
                    """,
                    (registry_id, sequence, digest),
                )
                conn.execute("COMMIT")
            else:
                conn.execute("ROLLBACK")
            return refusal
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
