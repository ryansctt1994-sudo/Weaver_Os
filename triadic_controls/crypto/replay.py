"""Replay protection primitives for triadic-controls TSC-001C.

This module provides the pilot replay-cache boundary for cryptographic
verification. The in-memory implementation is suitable for CI, simulation,
and single-process local development only. Production deployments require a
persistent implementation with atomic check-and-record semantics.
"""

from __future__ import annotations

import hashlib
import time
from typing import Optional, Protocol


class ReplayCacheProtocol(Protocol):
    """Abstract boundary for replay protection.

    Production implementations must guarantee atomic check_and_record.
    """

    def seen(self, replay_key: str, now: Optional[float] = None) -> bool:
        """Return True if replay_key is already present and unexpired."""
        ...

    def record(self, replay_key: str, expires_at: float) -> None:
        """Record replay_key until expires_at."""
        ...

    def check_and_record(
        self,
        replay_key: str,
        expires_at: float,
        now: Optional[float] = None,
    ) -> bool:
        """Atomically check whether replay_key exists, then record it if new.

        Returns True if the key was newly recorded. Returns False if replay was
        detected.
        """
        ...


def generate_replay_key(
    issuer_id: str,
    key_id: str,
    nonce_or_sequence: str,
    payload_type: str,
    system_id: str,
    scope_hash: str,
) -> str:
    """Generate a deterministic, domain-separated SHA-256 replay-cache key.

    Pipe separators prevent concatenation collisions such as:
    issuer="A", key="BC" versus issuer="AB", key="C".
    """

    raw = "|".join(
        [issuer_id, key_id, nonce_or_sequence, payload_type, system_id, scope_hash]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InMemoryReplayCache:
    """Pilot replay cache.

    Acceptable for CI, simulation, and single-process local development.
    Not acceptable as a production replay-protection boundary because state is
    lost on process restart and check-and-record is not multi-process atomic.
    """

    def __init__(self) -> None:
        self._entries: dict[str, float] = {}

    def seen(self, replay_key: str, now: Optional[float] = None) -> bool:
        now = now or time.time()
        self._prune(now)
        return replay_key in self._entries

    def record(self, replay_key: str, expires_at: float) -> None:
        self._entries[replay_key] = expires_at

    def check_and_record(
        self,
        replay_key: str,
        expires_at: float,
        now: Optional[float] = None,
    ) -> bool:
        now = now or time.time()
        self._prune(now)

        if replay_key in self._entries:
            return False

        self._entries[replay_key] = expires_at
        return True

    def _prune(self, now: float) -> None:
        """Opportunistically remove expired nonces to prevent memory leaks."""

        expired = [key for key, expires_at in self._entries.items() if expires_at <= now]
        for key in expired:
            del self._entries[key]
