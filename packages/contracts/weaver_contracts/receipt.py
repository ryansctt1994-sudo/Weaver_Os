"""wx-receipt-1: the receipt contract for the single-owner ReceiptLedger (ADR-0006).

A receipt records that one event was committed to one root of the Dual Ledger
(Authority Root or Rejection Root). Under ADR-0006 the ledger alone assigns
``sequence`` and ``predecessor_digest`` and creates the receipt *after* a
successful commit. Callers never build receipts. This module only defines the
shape, parses strictly, and recomputes ``receipt_digest``.

Fields deliberately left out (and why):

- ``replay_result`` / ``verifier_id`` (present in Lumen's receipt): replay is a
  later act by a read-only verifier. It produces a verification record, not a
  field on the commit receipt.
- signatures: ``receipt_digest`` is an integrity digest, not a signature. A
  signed receipt profile is blocked on Lumen-Nexus #13 / C-RCPT-001.

This module grants no authority and creates no evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .canonical import PROFILE_ID, CanonicalizationError, canonicalize, sha256_hex

SCHEMA_ID = "wx-receipt-1"
GENESIS_DIGEST = "0" * 64

ROOTS = frozenset({"AUTHORITY", "REJECTION"})
ADMISSIBILITY_BY_ROOT = {
    "AUTHORITY": frozenset({"ADMITTED"}),
    "REJECTION": frozenset({"REJECTED", "QUARANTINED"}),
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UPPER_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_UTC_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PLACEHOLDERS = frozenset({"TBD", "TODO", "PENDING", "PLACEHOLDER", "UNKNOWN"})

FIELDS = (
    "schema",
    "canonicalization",
    "ledger_id",
    "root",
    "sequence",
    "predecessor_digest",
    "event_type",
    "event_digest",
    "actor_id",
    "policy_version",
    "admissibility",
    "reason_code",
    "committed_at",
    "receipt_digest",
)


class ReceiptError(ValueError):
    """Raised when a receipt is outside the wx-receipt-1 contract."""


def _identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.match(value):
        raise ReceiptError(f"{name} must be an identifier string")
    if value.upper() in _PLACEHOLDERS:
        raise ReceiptError(f"{name} must not be a placeholder")
    return value


def _digest(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _SHA256.match(value):
        raise ReceiptError(f"{name} must be 64 lowercase hex characters")
    return value


def _token(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _UPPER_TOKEN.match(value):
        raise ReceiptError(f"{name} must be an UPPER_SNAKE token")
    return value


@dataclass(frozen=True)
class Receipt:
    schema: str
    canonicalization: str
    ledger_id: str
    root: str
    sequence: int
    predecessor_digest: str
    event_type: str
    event_digest: str
    actor_id: str
    policy_version: str
    admissibility: str
    reason_code: str | None
    committed_at: str
    receipt_digest: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA_ID:
            raise ReceiptError(f"schema must be {SCHEMA_ID!r}")
        if self.canonicalization != PROFILE_ID:
            raise ReceiptError(f"canonicalization must be {PROFILE_ID!r}")
        _identifier("ledger_id", self.ledger_id)
        if self.root not in ROOTS:
            raise ReceiptError(f"root must be one of {sorted(ROOTS)}")
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 0
        ):
            raise ReceiptError("sequence must be a non-negative integer")
        _digest("predecessor_digest", self.predecessor_digest)
        if (self.sequence == 0) != (self.predecessor_digest == GENESIS_DIGEST):
            raise ReceiptError(
                "predecessor_digest is the genesis digest exactly when sequence is 0"
            )
        _token("event_type", self.event_type)
        _digest("event_digest", self.event_digest)
        _identifier("actor_id", self.actor_id)
        _identifier("policy_version", self.policy_version)
        allowed = ADMISSIBILITY_BY_ROOT[self.root]
        if self.admissibility not in allowed:
            raise ReceiptError(f"{self.root} root requires admissibility in {sorted(allowed)}")
        if self.admissibility == "ADMITTED":
            if self.reason_code is not None:
                raise ReceiptError("an ADMITTED receipt must not carry a reason_code")
        else:
            _token("reason_code", self.reason_code)
        if not isinstance(self.committed_at, str) or not _UTC_SECONDS.match(self.committed_at):
            raise ReceiptError("committed_at must be UTC as YYYY-MM-DDTHH:MM:SSZ")
        _digest("receipt_digest", self.receipt_digest)
        if self.receipt_digest != compute_digest(self.body()):
            raise ReceiptError("receipt_digest does not match the receipt body")

    def body(self) -> dict[str, Any]:
        """Every field except ``receipt_digest``: the bytes the digest commits to."""
        data = asdict(self)
        del data["receipt_digest"]
        return data

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_canonical(self) -> bytes:
        return canonicalize(self.to_dict())


def compute_digest(body: Mapping[str, Any]) -> str:
    try:
        return sha256_hex(dict(body))
    except CanonicalizationError as exc:
        raise ReceiptError(f"receipt body is not canonicalizable: {exc}") from exc


def build(**fields: Any) -> Receipt:
    """Assemble a receipt from every field except the digest, then compute the digest.

    Intended for the ReceiptLedger only (ADR-0006). Callers outside the ledger
    must not use this to manufacture receipts.
    """
    body = {"schema": SCHEMA_ID, "canonicalization": PROFILE_ID, **fields}
    expected = set(FIELDS) - {"receipt_digest"}
    if set(body) != expected:
        missing = sorted(expected - set(body))
        extra = sorted(set(body) - expected)
        raise ReceiptError(f"fields mismatch; missing={missing} unexpected={extra}")
    return Receipt(**body, receipt_digest=compute_digest(body))


def from_dict(data: Any) -> Receipt:
    """Strictly parse a receipt mapping. Unknown or missing fields are rejected."""
    if not isinstance(data, Mapping):
        raise ReceiptError("receipt must be an object")
    keys = set(data)
    if keys != set(FIELDS):
        missing = sorted(set(FIELDS) - keys)
        extra = sorted(keys - set(FIELDS))
        raise ReceiptError(f"fields mismatch; missing={missing} unexpected={extra}")
    return Receipt(**{name: data[name] for name in FIELDS})
