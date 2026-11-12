"""Registry rollback contract (WVR-009).

A key registry carries ``registry_id`` and ``registry_sequence``. Given a sequence store,
``CryptoVerifier`` refuses an authenticated registry whose sequence is lower than the
highest the store has accepted for that ``registry_id``, or that reuses that sequence with
different content. Without this, an older registry that is still root-signed and inside its
validity window brings back keys a newer registry revoked.

The interface lives here. Implementations hold state, so they live in the runtime domain
(``weaver_runtime.registry_sequence``).
"""

from __future__ import annotations

from typing import Protocol

REGISTRY_ROLLBACK = "REGISTRY_ROLLBACK"
REGISTRY_SEQUENCE_CONFLICT = "REGISTRY_SEQUENCE_CONFLICT"

# SQLite INTEGER is a signed 64-bit value; a larger sequence cannot be stored.
MAX_REGISTRY_SEQUENCE = 2**63 - 1


class RegistrySequenceStoreProtocol(Protocol):
    """Per-registry high-water mark of authenticated sequences."""

    def advance(self, registry_id: str, sequence: int, digest: str) -> str | None:
        """Atomically compare ``(sequence, digest)`` with the stored mark and advance it.

        Returns ``None`` when the registry is accepted: first sight of ``registry_id``, a
        higher sequence, or the same sequence with the same digest (a reload). The stored
        mark is then ``(sequence, digest)``.

        Returns ``REGISTRY_ROLLBACK`` for a lower sequence and
        ``REGISTRY_SEQUENCE_CONFLICT`` for the same sequence with a different digest.
        A refusal leaves the stored mark unchanged.

        Callers must pass only registries whose root signature has already verified, so
        an unauthenticated registry can never move the mark.
        """
        ...


def decide(current: tuple[int, str] | None, sequence: int, digest: str) -> str | None:
    """The comparison every implementation must make, given the stored mark."""
    if current is None:
        return None
    stored_sequence, stored_digest = current
    if sequence < stored_sequence:
        return REGISTRY_ROLLBACK
    if sequence == stored_sequence and digest != stored_digest:
        return REGISTRY_SEQUENCE_CONFLICT
    return None
