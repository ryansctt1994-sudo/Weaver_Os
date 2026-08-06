"""Atomic persistent replay protection."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SQLiteReplayCache:
    """SQLite replay cache with an atomic uniqueness boundary.

    `BEGIN IMMEDIATE` serializes writers before expired entries are pruned and
    the candidate key is inserted. A duplicate key is rejected even across
    processes and restarts.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_keys (
                    replay_key TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL,
                    recorded_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS replay_expiry ON replay_keys(expires_at)"
            )

    def check_and_record(self, replay_key: str, expires_at: int, *, now: int | None = None) -> bool:
        if not replay_key:
            raise ValueError("replay_key must be non-empty")
        current = int(time.time()) if now is None else int(now)
        if expires_at <= current:
            return False

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM replay_keys WHERE expires_at <= ?", (current,))
            cursor = connection.execute(
                """
                INSERT INTO replay_keys(replay_key, expires_at, recorded_at)
                VALUES (?, ?, ?)
                ON CONFLICT(replay_key) DO NOTHING
                """,
                (replay_key, int(expires_at), current),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def contains(self, replay_key: str, *, now: int | None = None) -> bool:
        current = int(time.time()) if now is None else int(now)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM replay_keys WHERE replay_key = ? AND expires_at > ?",
                (replay_key, current),
            ).fetchone()
        return row is not None

