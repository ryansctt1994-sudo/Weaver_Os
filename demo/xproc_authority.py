"""WN-XPROC-AUTH-001: local, process-bound grant fixture."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DOMAIN = b"weaver/xproc-authority/v1\0"
FIELDS = {
    "issuer",
    "nonce",
    "actor",
    "action",
    "artifact",
    "policy",
    "epoch",
    "not_before",
    "expires",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Scope:
    actor: str
    action: str
    artifact: str
    policy: str
    epoch: int


class Authority:
    """An issuer and verifier sharing one process-local signing identity."""

    def __init__(self, *, epoch: int = 1):
        self.instance = secrets.token_hex(16)
        self._key = Ed25519PrivateKey.generate()
        self._public = self._key.public_key()
        self.epoch = epoch
        self.revoked: set[str] = set()
        self.used: set[str] = set()
        self.state: dict[str, object] = {"artifact": None, "revision": 0}
        self._lock = threading.Lock()

    def issue(self, scope: Scope, *, not_before: int, expires: int) -> dict:
        if expires <= not_before:
            raise ValueError("empty validity interval")
        body = {
            "issuer": self.instance,
            "nonce": secrets.token_hex(16),
            "actor": scope.actor,
            "action": scope.action,
            "artifact": scope.artifact,
            "policy": scope.policy,
            "epoch": scope.epoch,
            "not_before": not_before,
            "expires": expires,
        }
        signature = self._key.sign(DOMAIN + canonical(body))
        return {"body": body, "signature": base64.b64encode(signature).decode("ascii")}

    def consume(self, grant: object, scope: Scope, *, now: int) -> dict:
        with self._lock:
            before = digest(self.state)
            reason = self._validate(grant, scope, now)
            if reason is None:
                body = grant["body"]
                self.used.add(body["nonce"])
                self.state = {"artifact": scope.artifact, "revision": self.state["revision"] + 1}
            return {
                "accepted": reason is None,
                "reason": reason,
                "before": before,
                "after": digest(self.state),
                "state": dict(self.state),
            }

    def _validate(self, grant: object, scope: Scope, now: int) -> str | None:
        if not isinstance(grant, dict) or set(grant) != {"body", "signature"}:
            return "malformed"
        body, signature = grant["body"], grant["signature"]
        if not isinstance(body, dict) or set(body) != FIELDS or not isinstance(signature, str):
            return "malformed"
        if any(
            type(body[k]) is not str or not body[k]
            for k in ("issuer", "nonce", "actor", "action", "artifact", "policy")
        ):
            return "malformed"
        if (
            any(type(body[k]) is not int for k in ("epoch", "not_before", "expires"))
            or type(now) is not int
        ):
            return "malformed"
        if body["issuer"] != self.instance:
            return "foreign_issuer"
        try:
            raw = base64.b64decode(signature, validate=True)
            self._public.verify(raw, DOMAIN + canonical(body))
        except (ValueError, InvalidSignature):
            return "bad_signature"
        if (body["actor"], body["action"], body["artifact"], body["policy"], body["epoch"]) != (
            scope.actor,
            scope.action,
            scope.artifact,
            scope.policy,
            scope.epoch,
        ):
            return "scope_mismatch"
        if body["epoch"] != self.epoch:
            return "stale_epoch"
        if not body["not_before"] <= now < body["expires"]:
            return "outside_validity"
        if body["nonce"] in self.revoked:
            return "revoked"
        if body["nonce"] in self.used:
            return "reused"
        return None


def semantic_result(scope: Scope) -> str:
    """Stable decision input/result independent of the transport grant."""
    return digest(
        {
            "actor": scope.actor,
            "action": scope.action,
            "artifact": scope.artifact,
            "policy": scope.policy,
            "epoch": scope.epoch,
        }
    )
