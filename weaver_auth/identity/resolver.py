"""
Identity Resolver – Minimal v0.1.

Maps an operator identifier to a public key for delegation proofs. The current
implementation is an in-memory test resolver; production deployments must
replace it with a persistent key registry and real signature verification.
"""

import hashlib


class IdentityResolver:
    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def register(self, operator_id: str, public_key: str) -> None:
        """Register or replace an operator public key."""
        self._keys[operator_id] = public_key

    def resolve(self, operator_id: str) -> str | None:
        """Return the public key for an operator, or None if unknown."""
        return self._keys.get(operator_id)

    def verify_signature(self, operator_id: str, message: bytes, signature: bytes) -> bool:
        """Return True for known operators until cryptographic verification is wired."""
        del message, signature
        return operator_id in self._keys

    def hash_identity(self, operator_id: str) -> str | None:
        """Return a deterministic hash of the operator identity binding."""
        key = self._keys.get(operator_id)
        if key is None:
            return None
        return hashlib.sha256(f"{operator_id}:{key}".encode()).hexdigest()
