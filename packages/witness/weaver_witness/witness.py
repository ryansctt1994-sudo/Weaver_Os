"""A reference witness: signs wx-checkpoint-1 checkpoints, append-only and fork-refusing.

Who runs this matters more than what it does. A witness is only worth anything
if its key and its log are held by someone the ledger operator does not
control. This code cannot establish that. Run inside a test harness, or by the
operator, it is a simulated witness and everything it signs stays at W0.

Behaviour:

- It signs a checkpoint for a ledger only if the submitted snapshot verifies and
  **extends** the last checkpoint it signed for that ledger: each root is at
  least as long, and the entry at the old length has the old head as its
  ``receipt_digest``. Anything else is refused.
- Every signature and every refusal is appended to its own log (JSON Lines,
  WX-CJSON-1, fsynced). A refusal is evidence, not an error to hide.
- On start it re-reads the log and re-checks every checkpoint in it against its
  own public key and sequence numbers. A log it cannot account for stops it.

Bounds: one process per log, local file system. No locking across processes,
no key rotation (STEP7-EVIDENCE-CUSTODY.md leaves the rotation procedure open),
and no publication: getting checkpoints to verifiers is the caller's job.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict
from weaver_contracts.checkpoint import (
    CheckpointError,
    SignedCheckpoint,
    make_statement,
)
from weaver_contracts.ledger import ROOTS, RootHead
from weaver_contracts.receipt import GENESIS_DIGEST
from weaver_verifier.checkpoint import (
    chain_digests,
    extension_problem,
    load_pinned_keys,
    verify_checkpoint,
)
from weaver_verifier.ledger import verify_snapshot

SIGNED = "SIGNED"
UNCHANGED = "UNCHANGED"
REFUSED = "REFUSED"


class WitnessLogError(RuntimeError):
    """The witness log is corrupt or inconsistent. The witness refuses to start."""


@dataclass(frozen=True)
class WitnessDecision:
    status: str  # SIGNED | UNCHANGED | REFUSED
    reason: str
    checkpoint: dict[str, Any] | None = None


class Witness:
    def __init__(self, witness_id: str, private_key: Ed25519PrivateKey, log_path: str | Path):
        self.witness_id = witness_id
        self._key = private_key
        self.log_path = Path(log_path)
        self._pinned_self = load_pinned_keys({witness_id: self.public_key_hex})
        self._last: dict[str, SignedCheckpoint] = {}
        self._refusals: list[dict[str, Any]] = []
        self._load()

    @property
    def public_key_hex(self) -> str:
        return self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    def last_checkpoint(self, ledger_id: str) -> dict[str, Any] | None:
        last = self._last.get(ledger_id)
        return None if last is None else last.to_dict()

    def refusals(self) -> list[dict[str, Any]]:
        return [dict(record) for record in self._refusals]

    # --- log ----------------------------------------------------------------

    def _load(self) -> None:
        if not self.log_path.exists():
            return
        with self.log_path.open("rb") as handle:
            for lineno, line in enumerate(handle, 1):
                where = f"{self.log_path}:{lineno}"
                try:
                    record = parse_strict(line.rstrip(b"\n"))
                except CanonicalizationError as exc:
                    raise WitnessLogError(f"{where}: not WX-CJSON-1 ({exc})") from exc
                if not isinstance(record, dict):
                    raise WitnessLogError(f"{where}: record must be an object")
                kind = record.get("record")
                if kind == SIGNED and set(record) == {"record", "checkpoint"}:
                    self._replay_signed(where, record["checkpoint"])
                elif kind == REFUSED and set(record) == {"record", "ledger_id", "reason"}:
                    self._refusals.append(record)
                else:
                    raise WitnessLogError(f"{where}: unknown record")

    def _replay_signed(self, where: str, data: Any) -> None:
        try:
            checkpoint = verify_checkpoint(data, self._pinned_self)
        except CheckpointError as exc:
            raise WitnessLogError(
                f"{where}: checkpoint in the log does not verify ({exc})"
            ) from exc
        statement = checkpoint.statement
        previous = self._last.get(statement.ledger_id)
        expected_seq = 1 if previous is None else previous.statement.checkpoint_seq + 1
        if statement.checkpoint_seq != expected_seq:
            raise WitnessLogError(
                f"{where}: checkpoint_seq {statement.checkpoint_seq}, expected {expected_seq}"
            )
        if previous is not None:
            for root in ROOTS:
                if statement.heads()[root].length < previous.statement.heads()[root].length:
                    raise WitnessLogError(f"{where}: {root} regressed between checkpoints")
        self._last[statement.ledger_id] = checkpoint

    def _append(self, record: Mapping[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("ab") as handle:
            handle.write(canonicalize(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _refuse(self, ledger_id: str, reason: str) -> WitnessDecision:
        record = {"record": REFUSED, "ledger_id": ledger_id, "reason": reason}
        self._append(record)
        self._refusals.append(record)
        return WitnessDecision(REFUSED, reason)

    # --- submission ------------------------------------------------------------

    def submit(self, snapshot: Any) -> WitnessDecision:
        """Sign a checkpoint for ``snapshot`` if it extends the last one, else refuse."""
        ledger_id = snapshot.get("ledger_id") if isinstance(snapshot, Mapping) else None
        ledger_id = ledger_id if isinstance(ledger_id, str) else ""
        verdict = verify_snapshot(snapshot)
        if not verdict.ok:
            return self._refuse(ledger_id, f"INVALID_SNAPSHOT: {verdict.reason}")

        digests = chain_digests(snapshot)
        heads = {
            root: RootHead(len(chain), chain[-1] if chain else GENESIS_DIGEST)
            for root, chain in digests.items()
        }
        last = self._last.get(ledger_id)
        if last is not None:
            problem = extension_problem(digests, last.statement)
            if problem is not None:
                return self._refuse(ledger_id, problem)
            if last.statement.heads() == heads:
                return WitnessDecision(UNCHANGED, "already signed this state", last.to_dict())

        seq = 1 if last is None else last.statement.checkpoint_seq + 1
        try:
            statement = make_statement(ledger_id, self.witness_id, seq, heads)
        except CheckpointError as exc:
            return self._refuse(ledger_id, f"{exc.code}: {exc.detail}")
        checkpoint = SignedCheckpoint(statement, self._key.sign(statement.signing_bytes()))
        self._append({"record": SIGNED, "checkpoint": checkpoint.to_dict()})
        self._last[ledger_id] = checkpoint
        return WitnessDecision(SIGNED, f"checkpoint #{seq} signed", checkpoint.to_dict())
