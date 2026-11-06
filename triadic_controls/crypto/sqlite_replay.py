"""SQLite-backed replay cache for triadic-controls v0.5.0.

This module provides a persistent replay-protection boundary for production-like
use. Unlike InMemoryReplayCache, state survives process restarts and
check_and_record is delegated to SQLite's atomic uniqueness constraint.
"""

from __future__ import annotations

import math
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from .replay import ReplayCacheProtocol


class SQLiteReplayCache(ReplayCacheProtocol):
    """Persistent SQLite implementation of ReplayCacheProtocol.

    The replay_key column is a primary key. check_and_record uses
    INSERT ... ON CONFLICT DO NOTHING so duplicate submissions are rejected
    atomically by SQLite rather than by a separate read-then-write sequence.
    """

    def __init__(self, db_path: str | Path = "triadic_replay.db", *, create: bool = True) -> None:
        self.db_path = str(db_path)
        self._init_db(create=create)

    def _get_connection(self, *, create: bool = False) -> sqlite3.Connection:
        # Creation is confined to explicit initialization, never runtime replay checks.
        path = Path(self.db_path)
        if not create and (not path.is_file() or path.stat().st_size == 0):
            raise sqlite3.DatabaseError(
                "Replay state missing or empty; explicit initialization required"
            )
        uri = Path(self.db_path).resolve().as_uri() + ("?mode=rwc" if create else "?mode=rw")
        conn = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5)
        try:
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=FULL;")
        except sqlite3.Error:
            conn.close()
            raise
        return conn

    def _init_db(self, *, create: bool) -> None:
        with closing(self._get_connection(create=create)) as conn:
            if not create:
                # Missing/zeroed/malformed state must not become an empty valid cache.
                if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
                    raise sqlite3.DatabaseError("Replay state integrity check failed")
                conn.execute("SELECT replay_key, expires_at FROM replay_state LIMIT 0")
                return
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

    def seen(self, replay_key: str, now: float | None = None) -> bool:
        current_time = now if now is not None else time.time()
        self._validate_time(current_time)
        with closing(self._get_connection()) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM replay_state WHERE replay_key = ? AND expires_at > ?",
                (replay_key, current_time),
            )
            return cursor.fetchone() is not None

    def record(self, replay_key: str, expires_at: float) -> None:
        self._validate_time(expires_at)
        with closing(self._get_connection()) as conn:
            conn.execute(
                """
                INSERT INTO replay_state (replay_key, expires_at)
                VALUES (?, ?)
                ON CONFLICT(replay_key) DO UPDATE SET expires_at =
                    MAX(replay_state.expires_at, excluded.expires_at)
                """,
                (replay_key, expires_at),
            )

    def check_and_record(
        self,
        replay_key: str,
        expires_at: float,
        now: float | None = None,
    ) -> bool:
        current_time = now if now is not None else time.time()
        self._validate_time(current_time)
        self._validate_time(expires_at)
        if expires_at <= current_time:
            return False
        with closing(self._get_connection()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM replay_state WHERE expires_at <= ?", (current_time,))
            cursor = conn.execute(
                """
                INSERT INTO replay_state (replay_key, expires_at)
                VALUES (?, ?)
                ON CONFLICT(replay_key) DO NOTHING
                """,
                (replay_key, expires_at),
            )
            admitted = cursor.rowcount == 1
            conn.commit()
            return admitted

    def _prune(self, now: float) -> None:
        with closing(self._get_connection()) as conn:
            conn.execute(
                "DELETE FROM replay_state WHERE expires_at <= ?",
                (now,),
            )

    @staticmethod
    def _validate_time(value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Replay times must be finite numbers")
