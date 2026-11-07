"""Replay-protection contract for triadic-controls TSC-001C.

The interface (``ReplayCacheProtocol``) and the deterministic key derivation
(``generate_replay_key``). Implementations hold state, so they live in the runtime
domain (``weaver_runtime.replay_cache``). Moved from ``triadic_controls/crypto/replay.py``
in outline step 4.
"""

from __future__ import annotations

import hashlib
from typing import Protocol


class ReplayCacheProtocol(Protocol):
    """Abstract boundary for replay protection.

    Production implementations must guarantee atomic check_and_record.
    """

    def seen(self, replay_key: str, now: float | None = None) -> bool:
        """Return True if replay_key is already present and unexpired."""
        ...

    def record(self, replay_key: str, expires_at: float) -> None:
        """Record replay_key until expires_at."""
        ...

    def check_and_record(
        self,
        replay_key: str,
        expires_at: float,
        now: float | None = None,
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

    raw = "|".join([issuer_id, key_id, nonce_or_sequence, payload_type, system_id, scope_hash])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
