"""wx-checkpoint-1: the statement a witness signs about a ledger's Chronicle Root.

A checkpoint says: "witness W saw ledger L with these root lengths and heads, and
this is W's n-th checkpoint for L". It is signed with Ed25519 by a key the
ledger operator does not hold. The verifier accepts signatures only from keys
pinned out of band, never from keys found in the data under test.

This module defines shapes and the exact bytes that are signed. It does no
cryptography: signing lives with the witness and signature checks live in the
verifier. It grants no authority and creates no evidence. Whether a witness is
independent of the operator is a fact about people and organisations, which
nothing here can check.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .canonical import canonicalize
from .ledger import ROOTS, AnchorError, RootHead, chronicle_root

CHECKPOINT_SCHEMA = "wx-checkpoint-1"
SIGNATURE_ALGORITHM = "ed25519"
# Domain separation: these bytes can never be confused with any other signed format.
SIGNING_DOMAIN = b"wx-checkpoint-1\x00"

_STATEMENT_FIELDS = frozenset(
    {"schema", "ledger_id", "witness_id", "checkpoint_seq", "roots", "chronicle_root"}
)
_CHECKPOINT_FIELDS = frozenset({"statement", "signature"})
_SIGNATURE_FIELDS = frozenset({"algorithm", "value"})
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_SIGNATURE_HEX = re.compile(r"^[0-9a-f]{128}$")


class CheckpointError(ValueError):
    """Raised when data is outside the wx-checkpoint-1 contract.

    ``code`` is a stable reason: MALFORMED, UNPINNED_KEY or BAD_SIGNATURE.
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.match(value):
        raise CheckpointError("MALFORMED", f"{name} must be an identifier")
    return value


@dataclass(frozen=True)
class CheckpointStatement:
    ledger_id: str
    witness_id: str
    checkpoint_seq: int
    authority: RootHead
    rejection: RootHead
    chronicle_root: str

    def heads(self) -> dict[str, RootHead]:
        return {"AUTHORITY": self.authority, "REJECTION": self.rejection}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_SCHEMA,
            "ledger_id": self.ledger_id,
            "witness_id": self.witness_id,
            "checkpoint_seq": self.checkpoint_seq,
            "roots": {root: head.to_dict() for root, head in self.heads().items()},
            "chronicle_root": self.chronicle_root,
        }

    def signing_bytes(self) -> bytes:
        """The exact bytes a witness signs: domain prefix plus WX-CJSON-1 statement."""
        return SIGNING_DOMAIN + canonicalize(self.to_dict())


@dataclass(frozen=True)
class SignedCheckpoint:
    statement: CheckpointStatement
    signature: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement.to_dict(),
            "signature": {"algorithm": SIGNATURE_ALGORITHM, "value": self.signature.hex()},
        }


def make_statement(
    ledger_id: str, witness_id: str, checkpoint_seq: int, heads: Mapping[str, RootHead]
) -> CheckpointStatement:
    """Build a statement and compute its Chronicle Root from the heads."""
    _identifier("ledger_id", ledger_id)
    _identifier("witness_id", witness_id)
    if (
        not isinstance(checkpoint_seq, int)
        or isinstance(checkpoint_seq, bool)
        or checkpoint_seq < 1
    ):
        raise CheckpointError("MALFORMED", "checkpoint_seq must be an integer >= 1")
    try:
        root = chronicle_root(ledger_id, heads)
    except AnchorError as exc:
        raise CheckpointError("MALFORMED", str(exc)) from exc
    return CheckpointStatement(
        ledger_id=ledger_id,
        witness_id=witness_id,
        checkpoint_seq=checkpoint_seq,
        authority=heads["AUTHORITY"],
        rejection=heads["REJECTION"],
        chronicle_root=root,
    )


def parse_statement(data: Any) -> CheckpointStatement:
    """Strictly parse a statement and recompute its Chronicle Root."""
    if not isinstance(data, Mapping) or set(data) != _STATEMENT_FIELDS:
        raise CheckpointError(
            "MALFORMED", f"statement must have exactly the fields {sorted(_STATEMENT_FIELDS)}"
        )
    if data["schema"] != CHECKPOINT_SCHEMA:
        raise CheckpointError("MALFORMED", f"schema must be {CHECKPOINT_SCHEMA!r}")
    roots = data["roots"]
    if not isinstance(roots, Mapping) or set(roots) != set(ROOTS):
        raise CheckpointError("MALFORMED", f"roots must cover exactly {list(ROOTS)}")
    heads = {}
    for root in ROOTS:
        entry = roots[root]
        if not isinstance(entry, Mapping) or set(entry) != {"length", "head"}:
            raise CheckpointError("MALFORMED", f"{root} must have exactly length and head")
        try:
            heads[root] = RootHead(entry["length"], entry["head"])
        except AnchorError as exc:
            raise CheckpointError("MALFORMED", f"{root}: {exc}") from exc
    statement = make_statement(data["ledger_id"], data["witness_id"], data["checkpoint_seq"], heads)
    if statement.chronicle_root != data["chronicle_root"]:
        raise CheckpointError("MALFORMED", "chronicle_root does not match the stated heads")
    return statement


def parse_checkpoint(data: Any) -> SignedCheckpoint:
    """Strictly parse a signed checkpoint. Does not check the signature.

    Exact field sets are enforced, so a checkpoint cannot carry its own public key
    or any other field a verifier might be tempted to trust.
    """
    if not isinstance(data, Mapping) or set(data) != _CHECKPOINT_FIELDS:
        raise CheckpointError(
            "MALFORMED", f"checkpoint must have exactly the fields {sorted(_CHECKPOINT_FIELDS)}"
        )
    signature = data["signature"]
    if not isinstance(signature, Mapping) or set(signature) != _SIGNATURE_FIELDS:
        raise CheckpointError(
            "MALFORMED", f"signature must have exactly the fields {sorted(_SIGNATURE_FIELDS)}"
        )
    if signature["algorithm"] != SIGNATURE_ALGORITHM:
        raise CheckpointError("MALFORMED", f"signature algorithm must be {SIGNATURE_ALGORITHM!r}")
    value = signature["value"]
    if not isinstance(value, str) or not _SIGNATURE_HEX.match(value):
        raise CheckpointError("MALFORMED", "signature value must be 128 lowercase hex characters")
    return SignedCheckpoint(
        statement=parse_statement(data["statement"]), signature=bytes.fromhex(value)
    )
