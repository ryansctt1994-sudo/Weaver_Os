"""Shared shapes for the Dual Ledger: root heads, the Chronicle Root, anchors, snapshots.

The runtime (``weaver_runtime.ledger``) produces these and the read-only verifier
(``weaver_verifier.ledger``) checks them. Under UADR-0001 neither may import the
other, so the shapes they agree on live here.

An *anchor* is the value to publish somewhere the ledger's operator cannot
rewrite: an external append-only store, or witnesses. A hash chain on its own
is tamper-evident, not tamper-proof. Anyone who can rewrite the whole store can
recompute every digest forward. Only a comparison against an anchor held
elsewhere detects truncation or a full rewrite.

This module defines data rules only. It grants no authority and creates no evidence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .canonical import sha256_hex
from .receipt import GENESIS_DIGEST

ROOTS = ("AUTHORITY", "REJECTION")
ANCHOR_SCHEMA = "wx-chronicle-anchor-1"
SNAPSHOT_SCHEMA = "wx-ledger-snapshot-1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ANCHOR_FIELDS = frozenset({"schema", "ledger_id", "roots", "chronicle_root"})


class AnchorError(ValueError):
    """Raised when an anchor is outside the wx-chronicle-anchor-1 contract."""


@dataclass(frozen=True)
class RootHead:
    """Length and head digest of one root's chain."""

    length: int
    head: str

    def __post_init__(self) -> None:
        if not isinstance(self.length, int) or isinstance(self.length, bool) or self.length < 0:
            raise AnchorError("length must be a non-negative integer")
        if not isinstance(self.head, str) or not _SHA256.match(self.head):
            raise AnchorError("head must be 64 lowercase hex characters")
        if (self.length == 0) != (self.head == GENESIS_DIGEST):
            raise AnchorError("head is the genesis digest exactly when length is 0")

    def to_dict(self) -> dict[str, Any]:
        return {"length": self.length, "head": self.head}


EMPTY_HEAD = RootHead(0, GENESIS_DIGEST)


def chronicle_root(ledger_id: str, heads: Mapping[str, RootHead]) -> str:
    """Digest binding both roots' heads under one Chronicle Root."""
    if set(heads) != set(ROOTS):
        raise AnchorError(f"heads must cover exactly {list(ROOTS)}")
    return sha256_hex(
        {
            "schema": ANCHOR_SCHEMA,
            "ledger_id": ledger_id,
            "roots": {root: heads[root].to_dict() for root in ROOTS},
        }
    )


@dataclass(frozen=True)
class Anchor:
    ledger_id: str
    authority: RootHead
    rejection: RootHead
    chronicle_root: str

    def heads(self) -> dict[str, RootHead]:
        return {"AUTHORITY": self.authority, "REJECTION": self.rejection}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ANCHOR_SCHEMA,
            "ledger_id": self.ledger_id,
            "roots": {root: head.to_dict() for root, head in self.heads().items()},
            "chronicle_root": self.chronicle_root,
        }


def make_anchor(ledger_id: str, heads: Mapping[str, RootHead]) -> Anchor:
    return Anchor(
        ledger_id=ledger_id,
        authority=heads["AUTHORITY"],
        rejection=heads["REJECTION"],
        chronicle_root=chronicle_root(ledger_id, heads),
    )


def parse_anchor(data: Any) -> Anchor:
    """Strictly parse an anchor and recompute its Chronicle Root."""
    if not isinstance(data, Mapping) or set(data) != _ANCHOR_FIELDS:
        raise AnchorError(f"anchor must have exactly the fields {sorted(_ANCHOR_FIELDS)}")
    if data["schema"] != ANCHOR_SCHEMA:
        raise AnchorError(f"schema must be {ANCHOR_SCHEMA!r}")
    if not isinstance(data["ledger_id"], str) or not data["ledger_id"]:
        raise AnchorError("ledger_id must be a non-empty string")
    roots = data["roots"]
    if not isinstance(roots, Mapping) or set(roots) != set(ROOTS):
        raise AnchorError(f"roots must cover exactly {list(ROOTS)}")
    heads = {}
    for root in ROOTS:
        entry = roots[root]
        if not isinstance(entry, Mapping) or set(entry) != {"length", "head"}:
            raise AnchorError(f"{root} must have exactly length and head")
        heads[root] = RootHead(entry["length"], entry["head"])
    anchor = make_anchor(data["ledger_id"], heads)
    if anchor.chronicle_root != data["chronicle_root"]:
        raise AnchorError("chronicle_root does not match the anchored heads")
    return anchor
