"""ReceiptLedger: the single owner of Dual Ledger linkage state (Lumen-Nexus ADR-0006).

Callers submit event *content* and a gate decision (admit or reject). They never
supply, read back into, or mutate a sequence number, predecessor digest, chain
head, or receipt digest. The ledger alone:

1. admits the event as WX-CJSON-1 canonical bytes;
2. selects the predecessor (the current head of the target root);
3. assigns the next sequence number for that root;
4. appends the event and its receipt atomically, in one SQLite transaction;
5. advances and persists the root's head in the same transaction;
6. returns the receipt only after the transaction has committed;
7. exports read-only snapshots and anchors for verifiers.

The ledger records gate decisions. It does not make them. Whether an event is
admitted is decided upstream. The ledger only refuses data that cannot be
recorded under the contracts (non-canonical content, invalid receipt fields).

Storage is SQLite in WAL mode with ``synchronous=FULL``. Appends from several
threads or processes are serialized by ``BEGIN IMMEDIATE``. Each append either
commits with the next sequence number or raises ``LedgerBusy``, so there is
always one total order.

Before extending a root, the ledger checks that the stored head row agrees with
the root's last entry. That is a local guard. It does not re-verify the whole
chain, which is the verifier's job (``weaver_verifier.ledger``).

Storage assumptions: the single-owner guarantee holds for writers that go through
``ReceiptLedger``. A process that writes the SQLite file directly bypasses it. The head
guard catches some such edits, and the verifier catches the rest only with an external
anchor. Serialization relies on SQLite's file locking, and WAL mode needs shared memory,
so the store must be on a local file system: SQLite documents that WAL does not work over
network file systems.

This module records evidence. It grants no authority.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from types import TracebackType
from typing import Any

from weaver_contracts.canonical import (
    CanonicalizationError,
    canonicalize,
    parse_strict,
    sha256_hex,
)
from weaver_contracts.ledger import (
    ROOTS,
    SNAPSHOT_SCHEMA,
    Anchor,
    RootHead,
    make_anchor,
)
from weaver_contracts.receipt import GENESIS_DIGEST, Receipt, ReceiptError, build

STORE_SCHEMA = "wx-receipt-ledger-store-1"


class LedgerError(RuntimeError):
    """Base class for ReceiptLedger failures."""


class AdmissionError(LedgerError):
    """The event or receipt fields cannot be recorded under the contracts."""


class LedgerBusy(LedgerError):
    """Another writer held the store for longer than the busy timeout."""


class LedgerCorrupted(LedgerError):
    """The stored head disagrees with the stored entries; the ledger refuses to extend it."""


def utc_now_seconds() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS entries ("
    " root TEXT NOT NULL, sequence INTEGER NOT NULL, event BLOB NOT NULL,"
    " receipt BLOB NOT NULL, receipt_digest TEXT NOT NULL,"
    " PRIMARY KEY (root, sequence))",
    "CREATE TABLE IF NOT EXISTS heads ("
    " root TEXT PRIMARY KEY, length INTEGER NOT NULL, head TEXT NOT NULL)",
)


class ReceiptLedger:
    """Single-owner, SQLite-backed Dual Ledger."""

    def __init__(
        self,
        path: str | Path,
        *,
        ledger_id: str,
        clock: Callable[[], str] = utc_now_seconds,
        busy_timeout_ms: int = 5000,
    ) -> None:
        self._path = Path(path)
        self._ledger_id = ledger_id
        self._clock = clock
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self._path),
            isolation_level=None,
            check_same_thread=False,
            timeout=busy_timeout_ms / 1000,
        )
        self._conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._initialize()

    # ------------------------------------------------------------------ setup

    def _begin(self) -> None:
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc) or "busy" in str(exc):
                raise LedgerBusy(str(exc)) from exc
            raise

    def _initialize(self) -> None:
        with self._lock:
            self._begin()
            try:
                for statement in _SCHEMA_SQL:
                    self._conn.execute(statement)
                rows = dict(self._conn.execute("SELECT key, value FROM meta").fetchall())
                if not rows:
                    self._conn.executemany(
                        "INSERT INTO meta (key, value) VALUES (?, ?)",
                        [("store_schema", STORE_SCHEMA), ("ledger_id", self._ledger_id)],
                    )
                    self._conn.executemany(
                        "INSERT INTO heads (root, length, head) VALUES (?, 0, ?)",
                        [(root, GENESIS_DIGEST) for root in ROOTS],
                    )
                elif rows.get("store_schema") != STORE_SCHEMA:
                    raise LedgerError(f"unsupported store schema: {rows.get('store_schema')!r}")
                elif rows.get("ledger_id") != self._ledger_id:
                    raise LedgerError(
                        f"store belongs to ledger {rows.get('ledger_id')!r}, "
                        f"not {self._ledger_id!r}"
                    )
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> ReceiptLedger:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def ledger_id(self) -> str:
        return self._ledger_id

    # ----------------------------------------------------------------- writes

    def admit(
        self,
        event_type: str,
        event: Mapping[str, Any],
        *,
        actor_id: str,
        policy_version: str,
    ) -> Receipt:
        """Record an admitted event on the Authority Root."""
        return self._commit(
            root="AUTHORITY",
            event_type=event_type,
            event=event,
            actor_id=actor_id,
            policy_version=policy_version,
            admissibility="ADMITTED",
            reason_code=None,
        )

    def reject(
        self,
        event_type: str,
        event: Mapping[str, Any],
        *,
        actor_id: str,
        policy_version: str,
        reason_code: str,
        quarantine: bool = False,
    ) -> Receipt:
        """Record a denied or quarantined attempt on the Rejection Root."""
        return self._commit(
            root="REJECTION",
            event_type=event_type,
            event=event,
            actor_id=actor_id,
            policy_version=policy_version,
            admissibility="QUARANTINED" if quarantine else "REJECTED",
            reason_code=reason_code,
        )

    def _commit(
        self,
        *,
        root: str,
        event_type: str,
        event: Mapping[str, Any],
        actor_id: str,
        policy_version: str,
        admissibility: str,
        reason_code: str | None,
    ) -> Receipt:
        if not isinstance(event, Mapping):
            raise AdmissionError("event content must be a JSON object")
        try:
            event_bytes = canonicalize(event)
        except CanonicalizationError as exc:
            raise AdmissionError(f"event is not WX-CJSON-1 canonicalizable: {exc}") from exc
        event_digest = sha256_hex(parse_strict(event_bytes))

        with self._lock:
            self._begin()
            try:
                head = self._checked_head(root)
                try:
                    receipt = build(
                        ledger_id=self._ledger_id,
                        root=root,
                        sequence=head.length,
                        predecessor_digest=head.head,
                        event_type=event_type,
                        event_digest=event_digest,
                        actor_id=actor_id,
                        policy_version=policy_version,
                        admissibility=admissibility,
                        reason_code=reason_code,
                        committed_at=self._clock(),
                    )
                except ReceiptError as exc:
                    raise AdmissionError(str(exc)) from exc
                self._insert_entry(receipt, event_bytes)
                self._advance_head(receipt)
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
        return receipt

    def _checked_head(self, root: str) -> RootHead:
        row = self._conn.execute(
            "SELECT length, head FROM heads WHERE root = ?", (root,)
        ).fetchone()
        if row is None:
            raise LedgerCorrupted(f"missing head row for {root}")
        length, head = row
        last = self._conn.execute(
            "SELECT sequence, receipt_digest FROM entries WHERE root = ?"
            " ORDER BY sequence DESC LIMIT 1",
            (root,),
        ).fetchone()
        count = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE root = ?", (root,)
        ).fetchone()[0]
        expected = (None, GENESIS_DIGEST) if length == 0 else (length - 1, head)
        actual = (None, GENESIS_DIGEST) if last is None else (last[0], last[1])
        if count != length or actual != expected:
            raise LedgerCorrupted(
                f"{root} head row (length={length}) disagrees with stored entries "
                f"(count={count}); refusing to extend"
            )
        try:
            return RootHead(length, head)
        except ValueError as exc:
            raise LedgerCorrupted(f"{root} head row is malformed: {exc}") from exc

    def _insert_entry(self, receipt: Receipt, event_bytes: bytes) -> None:
        self._conn.execute(
            "INSERT INTO entries (root, sequence, event, receipt, receipt_digest)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                receipt.root,
                receipt.sequence,
                event_bytes,
                receipt.to_canonical(),
                receipt.receipt_digest,
            ),
        )

    def _advance_head(self, receipt: Receipt) -> None:
        cursor = self._conn.execute(
            "UPDATE heads SET length = ?, head = ? WHERE root = ? AND length = ?",
            (receipt.sequence + 1, receipt.receipt_digest, receipt.root, receipt.sequence),
        )
        if cursor.rowcount != 1:
            raise LedgerCorrupted(f"{receipt.root} head moved during the transaction")

    # ------------------------------------------------------------------ reads

    def heads(self) -> dict[str, RootHead]:
        with self._lock:
            rows = self._conn.execute("SELECT root, length, head FROM heads").fetchall()
        found = {root: RootHead(length, head) for root, length, head in rows}
        if set(found) != set(ROOTS):
            raise LedgerCorrupted("head rows do not cover both roots")
        return found

    def anchor(self) -> Anchor:
        """The value to publish externally so truncation and rewrites become detectable."""
        return make_anchor(self._ledger_id, self.heads())

    def snapshot(self) -> dict[str, Any]:
        """A consistent, freshly built copy of the store for read-only verification.

        Nothing returned here aliases stored state. Mutating it changes nothing
        in the ledger.
        """
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                rows = self._conn.execute(
                    "SELECT root, event, receipt FROM entries ORDER BY root, sequence"
                ).fetchall()
            finally:
                self._conn.execute("COMMIT")
        roots: dict[str, list[dict[str, Any]]] = {root: [] for root in ROOTS}
        for root, event, receipt in rows:
            if root not in roots:
                raise LedgerCorrupted(f"entry on unknown root {root!r}")
            roots[root].append(
                {"event": bytes(event).decode("utf-8"), "receipt": parse_strict(bytes(receipt))}
            )
        return {"schema": SNAPSHOT_SCHEMA, "ledger_id": self._ledger_id, "roots": roots}
