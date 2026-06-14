"""
Identity Resolver – Minimal Stub v0.1
Maps operator_id to a public key for delegation proofs.
Replace with actual key registry in production.
"""
from typing import Optional
import hashlib


class IdentityResolver:
    def __init__(self):
        # In-memory store: operator_id -> public_key_hex
        self._keys = {}

    def register(self, operator_id: str, public_key: str) -> None:
        """Register a new operator with their public key."""
        self._keys[operator_id] = public_key

    def resolve(self, operator_id: str) -> Optional[str]:
        """Return the public key for a given operator ID, or None if not found."""
        return self._keys.get(operator_id)

    def verify_signature(self, operator_id: str, message: bytes, signature: bytes) -> bool:
        """Stub verification – always returns True for known operators, False otherwise."""
        return operator_id in self._keys

    def hash_identity(self, operator_id: str) -> Optional[str]:
        """Return a deterministic hash of the operator's identity."""
        key = self._keys.get(operator_id)
        if key is None:
            return None
        return hashlib.sha256(f"{operator_id}:{key}".encode()).hexdigest()
