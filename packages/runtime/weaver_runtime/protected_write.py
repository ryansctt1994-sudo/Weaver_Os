"""WEAVER-VERTICAL-001: one bounded, owner-mediated SQLite write.

Research-only integration. The owner is trusted; the requester must not control its
constructor, signing-key trust root, SQLite path, authorizer or effect hook. This module
alone does NOT isolate a caller running with the owner's filesystem permissions.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import AuthorizationDecision, Proposal

from .gate import ExecutionContext, ExecutionGate, GateOutcome, VetoSource
from .ledger import ReceiptLedger

GRANT_DOMAIN = b"WEAVER-VERTICAL-001-GRANT\x00"
GRANT_FIELDS = frozenset(
    {"issuer_id", "audience", "grant_id", "proposal_sha256", "valid_from", "valid_until"}
)
_KEY = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


class ProtectedWriteOwner:
    """Trusted application-side SQLite owner, not an OS security boundary.

    The issuer key, accepted key names, database path and verifier are installed by
    the trusted host at construction. A requester may supply only a Proposal and a
    signed grant envelope. All persisted writes go through the same ReceiptLedger
    transaction as EXECUTION_COMMITTED; rejected requests never touch the resource.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        trusted_public_key: bytes,
        issuer_id: str,
        allowed_keys: frozenset[str],
        veto: VetoSource,
        clock: Callable[[], int] = lambda: int(time.time()),
        ledger_id: str = "weaver-vertical-001",
        audience: str = "weaver-vertical-001",
    ) -> None:
        if not isinstance(issuer_id, str) or not issuer_id:
            raise ValueError("issuer_id is required")
        if not isinstance(audience, str) or not audience:
            raise ValueError("audience is required")
        if not allowed_keys or not all(
            isinstance(key, str) and _KEY.fullmatch(key) for key in allowed_keys
        ):
            raise ValueError("allowed_keys must be nonempty valid key names")
        self._public_key = Ed25519PublicKey.from_public_bytes(trusted_public_key)
        self._issuer_id = issuer_id
        self._audience = audience
        self._allowed_keys = frozenset(allowed_keys)
        self._clock = clock
        self._veto = veto
        self._path = Path(db_path)
        self._ledger = ReceiptLedger(self._path, ledger_id=ledger_id)
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS protected_kv ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL, proposal_id TEXT NOT NULL)"
            )

    def close(self) -> None:
        self._ledger.close()

    def __enter__(self) -> ProtectedWriteOwner:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _authorize(
        self, proposal: Proposal, envelope: Mapping[str, Any] | None
    ) -> AuthorizationDecision:
        denial = AuthorizationDecision(
            False, "denied-grant", valid_until=0, reason_code="GRANT_INVALID"
        )
        try:
            if not isinstance(envelope, Mapping) or set(envelope) != {"grant", "signature"}:
                return denial
            raw = envelope["grant"]
            if not isinstance(raw, Mapping) or set(raw) != GRANT_FIELDS:
                return denial
            grant = dict(raw)
            if (
                grant["issuer_id"] != self._issuer_id
                or grant["audience"] != self._audience
                or not isinstance(grant["grant_id"], str)
                or type(grant["valid_from"]) is not int
                or type(grant["valid_until"]) is not int
            ):
                return denial
            expected = hashlib.sha256(canonicalize(proposal.to_dict())).hexdigest()
            if grant["proposal_sha256"] != expected:
                return denial
            now = self._clock()
            if not grant["valid_from"] <= now < grant["valid_until"]:
                return denial
            signature = envelope["signature"]
            if not isinstance(signature, str):
                return denial
            signature_bytes = base64.b64decode(
                signature.encode("ascii"), altchars=b"-_", validate=True
            )
            self._public_key.verify(signature_bytes, GRANT_DOMAIN + canonicalize(grant))
            return AuthorizationDecision(
                True, grant["grant_id"], valid_until=grant["valid_until"]
            )
        except (ValueError, TypeError, KeyError, OverflowError, UnicodeError,
                binascii.Error, InvalidSignature):
            return denial

    def _validated_payload(self, proposal: Mapping[str, Any]) -> tuple[str, str]:
        if proposal.get("action") != "WRITE_KEY":
            raise ValueError("only WRITE_KEY is supported")
        payload = proposal.get("payload")
        if not isinstance(payload, dict) or set(payload) != {"key", "value"}:
            raise ValueError("WRITE_KEY payload must have exactly key and value")
        key, value = payload["key"], payload["value"]
        if (
            not isinstance(key, str)
            or key not in self._allowed_keys
            or not isinstance(value, str)
            or not 0 < len(value) <= 256
        ):
            raise ValueError("key or value is outside owner scope")
        return key, value

    def _stage(self, context: ExecutionContext) -> dict[str, str]:
        context.checkpoint()
        key, value = self._validated_payload(context.proposal.to_dict())
        return {"effect": "WRITE_KEY", "key": key, "value": value}

    def _effect(
        self,
        conn: sqlite3.Connection,
        proposal: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> None:
        key, value = self._validated_payload(proposal)
        if dict(result) != {"effect": "WRITE_KEY", "key": key, "value": value}:
            raise ValueError("staged result disagrees with pinned proposal")
        conn.execute(
            "INSERT INTO protected_kv (key, value, proposal_id) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "proposal_id=excluded.proposal_id",
            (key, value, proposal["proposal_id"]),
        )

    def submit(
        self,
        proposal: Proposal,
        signed_grant: Mapping[str, Any] | None,
    ) -> GateOutcome:
        # One gate per request: the bound authorizer and commit effect are chosen
        # by this owner, never supplied to execute() by the requester.
        gate = ExecutionGate(
            self._ledger,
            veto=self._veto,
            authorize=lambda p: self._authorize(p, signed_grant),
            atomic_effect=self._effect,
            clock=self._clock,
            gate_id="protected-write-owner",
        )
        return gate.execute(proposal, self._stage)

    def rows(self) -> dict[str, str]:
        # Read-only verification view. Does not return a write-capable connection.
        with sqlite3.connect(self._path.as_uri() + "?mode=ro", uri=True) as conn:
            return dict(conn.execute("SELECT key, value FROM protected_kv ORDER BY key"))

    def snapshot(self) -> dict[str, Any]:
        return self._ledger.snapshot()

    def anchor(self) -> dict[str, Any]:
        return self._ledger.anchor().to_dict()
