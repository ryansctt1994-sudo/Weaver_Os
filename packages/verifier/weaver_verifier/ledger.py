"""Read-only verification of ReceiptLedger snapshots and anchors.

Under UADR-0001 this module imports only from ``weaver_contracts``. It cannot
reach the ledger's code, so it cannot latch, execute, append to, or repair the
ledger (ADR-0006). It takes plain data and returns a verdict, and it never
modifies its input.

Checks, per root and per entry:

- the snapshot and entry shapes are exact (no extra or missing fields);
- the stored event bytes are WX-CJSON-1 canonical;
- the receipt satisfies the wx-receipt-1 contract (including its own digest);
- the receipt names this ledger and this root;
- ``sequence`` equals the entry's position;
- ``predecessor_digest`` equals the previous receipt's digest (genesis for the first);
- ``event_digest`` equals the SHA-256 of the stored event bytes.

With an anchor, it also checks each root's length and head, and the Chronicle
Root. Without one, truncation and full forward-recompute rewrites are **not**
detectable, and the verdict says so.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from weaver_contracts.canonical import is_canonical
from weaver_contracts.ledger import (
    ROOTS,
    SNAPSHOT_SCHEMA,
    AnchorError,
    RootHead,
    chronicle_root,
    parse_anchor,
)
from weaver_contracts.receipt import GENESIS_DIGEST, ReceiptError, from_dict

_SNAPSHOT_FIELDS = frozenset({"schema", "ledger_id", "roots"})
_ENTRY_FIELDS = frozenset({"event", "receipt"})


@dataclass(frozen=True)
class LedgerVerdict:
    ok: bool
    reason: str
    anchored: bool = False
    chronicle_root: str | None = None


def _fail(reason: str) -> LedgerVerdict:
    return LedgerVerdict(ok=False, reason=reason)


def verify_snapshot(snapshot: Any, *, anchor: Any = None) -> LedgerVerdict:
    """Verify a ledger snapshot, optionally against an externally held anchor."""
    if not isinstance(snapshot, Mapping) or set(snapshot) != _SNAPSHOT_FIELDS:
        return _fail(f"snapshot must have exactly the fields {sorted(_SNAPSHOT_FIELDS)}")
    if snapshot["schema"] != SNAPSHOT_SCHEMA:
        return _fail(f"snapshot schema must be {SNAPSHOT_SCHEMA!r}")
    ledger_id = snapshot["ledger_id"]
    roots = snapshot["roots"]
    if not isinstance(roots, Mapping) or set(roots) != set(ROOTS):
        return _fail(f"snapshot roots must be exactly {list(ROOTS)}")

    heads: dict[str, RootHead] = {}
    for root in ROOTS:
        entries = roots[root]
        if not isinstance(entries, list):
            return _fail(f"{root} entries must be a list")
        previous = GENESIS_DIGEST
        for index, entry in enumerate(entries):
            where = f"{root}[{index}]"
            if not isinstance(entry, Mapping) or set(entry) != _ENTRY_FIELDS:
                return _fail(f"{where}: entry must have exactly event and receipt")
            event = entry["event"]
            if not isinstance(event, str):
                return _fail(f"{where}: event must be canonical JSON text")
            event_bytes = event.encode("utf-8")
            if not is_canonical(event_bytes):
                return _fail(f"{where}: event bytes are not WX-CJSON-1 canonical")
            try:
                receipt = from_dict(entry["receipt"])
            except ReceiptError as exc:
                return _fail(f"{where}: receipt invalid: {exc}")
            if receipt.ledger_id != ledger_id:
                return _fail(f"{where}: receipt belongs to ledger {receipt.ledger_id!r}")
            if receipt.root != root:
                return _fail(f"{where}: receipt is for root {receipt.root}")
            if receipt.sequence != index:
                return _fail(f"{where}: sequence mismatch (receipt says {receipt.sequence})")
            if receipt.predecessor_digest != previous:
                return _fail(f"{where}: broken link (predecessor does not match prior receipt)")
            if receipt.event_digest != hashlib.sha256(event_bytes).hexdigest():
                return _fail(f"{where}: event digest mismatch (event content changed)")
            previous = receipt.receipt_digest
        heads[root] = RootHead(len(entries), previous)

    root_digest = chronicle_root(ledger_id, heads)
    if anchor is None:
        return LedgerVerdict(
            ok=True,
            reason="chains internally valid; truncation and full rewrites are not "
            "detectable without an anchor",
            anchored=False,
            chronicle_root=root_digest,
        )

    try:
        expected = parse_anchor(anchor)
    except AnchorError as exc:
        return _fail(f"anchor invalid: {exc}")
    if expected.ledger_id != ledger_id:
        return _fail(f"anchor is for ledger {expected.ledger_id!r}")
    for root, want in expected.heads().items():
        got = heads[root]
        if got.length != want.length:
            return _fail(
                f"{root}: length {got.length} != anchored {want.length} "
                "(truncation or insertion detected)"
            )
        if got.head != want.head:
            return _fail(f"{root}: head != anchored head (rewrite detected)")
    if root_digest != expected.chronicle_root:
        return _fail("chronicle root != anchored chronicle root")
    return LedgerVerdict(
        ok=True,
        reason="chains valid and match the anchor",
        anchored=True,
        chronicle_root=root_digest,
    )
