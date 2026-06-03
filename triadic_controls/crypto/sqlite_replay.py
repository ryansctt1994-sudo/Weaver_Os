"""SQLite-backed replay cache for triadic-controls v0.5.0.

This module provides a persistent replay-protection boundary for production-like
use. Unlike InMemoryReplayCache, state survives process restarts and
check_and_record is delegated to SQLite's atomic uniqueness constraint.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional, Union

from .replay import ReplayCacheProtocol


class SQLiteReplayCache(ReplayCacheProtocol):
    """Persistent SQLite implementation of ReplayCacheProtocol.

    The replay_key column is a primary key. check_and_record uses
    INSERT ... ON CONFLICT DO NOTHING so duplicate submissions are rejected
    atomically by SQLite rather than by a separate read-then-write sequence.
    """

    def __init__(self, db_path: Union[str, Path] = "triadic_replay.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_state (
                    replay_key TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_replay_state_expires_at
                ON replay_state(expires_at)
                """
            )

    def seen(self, replay_key: str, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.time()
        self._prune(current_time)
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM replay_state WHERE replay_key = ?",
                (replay_key,),
            )
            return cursor.fetchone() is not None

    def record(self, replay_key: str, expires_at: float) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO replay_state (replay_key, expires_at)
                VALUES (?, ?)
                """,
                (replay_key, expires_at),
            )

    def check_and_record(
        self,
        replay_key: str,
        expires_at: float,
        now: Optional[float] = None,
    ) -> bool:
        current_time = now if now is not None else time.time()
        self._prune(current_time)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO replay_state (replay_key, expires_at)
                VALUES (?, ?)
                ON CONFLICT(replay_key) DO NOTHING
                """,
                (replay_key, expires_at),
            )
            return cursor.rowcount == 1

    def _prune(self, now: float) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM replay_state WHERE expires_at <= ?",
                (now,),
            )
