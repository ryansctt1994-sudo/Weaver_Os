"""Check a ledger snapshot against wx-checkpoint-1 witness checkpoints.

Read-only, like the rest of the verifier: it takes plain data and returns a report.

What it checks:

- the snapshot's chains are internally valid (``verify_snapshot``);
- every checkpoint parses strictly and is signed by a key in ``pinned_keys``,
  which the caller supplies out of band. Keys are never taken from the input;
- no two checkpoints disagree about the head at the same length (split view),
  and no witness contradicts its own earlier checkpoints;
- the snapshot extends every checkpoint: for each root it is at least as long,
  and its entry at the checkpoint's length has the checkpoint's head as its
  ``receipt_digest``. A shorter snapshot is REGRESSED, a different entry FORKED.

What it cannot check, and so never claims:

- that a witness is independent of the ledger operator. That is a fact about
  people and organisations. Every report says ``independence: NOT_ESTABLISHED``;
- that history is authentic before the first checkpoint. A rewrite that no
  witness ever saw is indistinguishable from the original;
- anything after the latest checkpoint. The report counts those entries and
  never calls them covered;
- wall-clock time. Checkpoints bind content, so staleness is measured in
  entries, not in hours.

There is deliberately no WITNESSED status. A consistent result is
CHECKPOINT_CONSISTENT, with the number of distinct pinned witnesses alongside.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from weaver_contracts.checkpoint import (
    CheckpointError,
    CheckpointStatement,
    SignedCheckpoint,
    parse_checkpoint,
)
from weaver_contracts.ledger import ROOTS

from .ledger import verify_snapshot

REFUSED = "REFUSED"
UNWITNESSED = "UNWITNESSED"
CHECKPOINT_CONSISTENT = "CHECKPOINT_CONSISTENT"

INDEPENDENCE = "NOT_ESTABLISHED"
WITNESS_LEVEL = "W0"

_PUBLIC_KEY_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CustodyReport:
    status: str
    reason: str
    ledger_id: str | None = None
    # Distinct pinned witnesses whose checkpoints the snapshot extends.
    witnesses: tuple[str, ...] = ()
    corroboration: str = "NONE"  # NONE | UNCORROBORATED (one witness) | CORROBORATED (two or more)
    covered: dict[str, int] = field(
        default_factory=dict
    )  # per root: length covered by a checkpoint
    unwitnessed_entries: dict[str, int] = field(default_factory=dict)
    freshness: str = "NOT_EVALUATED"
    independence: str = INDEPENDENCE
    witness_level: str = WITNESS_LEVEL

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "ledger_id": self.ledger_id,
            "witnesses": list(self.witnesses),
            "corroboration": self.corroboration,
            "covered": dict(self.covered),
            "unwitnessed_entries": dict(self.unwitnessed_entries),
            "freshness": self.freshness,
            "independence": self.independence,
            "witness_level": self.witness_level,
        }


def _refused(reason: str, ledger_id: str | None = None) -> CustodyReport:
    return CustodyReport(status=REFUSED, reason=reason, ledger_id=ledger_id)


def load_pinned_keys(pinned_keys: Mapping[str, str]) -> dict[str, Ed25519PublicKey]:
    """Parse ``{witness_id: public_key_hex}``. Raises CheckpointError on bad input."""
    if not isinstance(pinned_keys, Mapping):
        raise CheckpointError("MALFORMED", "pinned_keys must map witness_id to a public key")
    keys = {}
    for witness_id, key_hex in pinned_keys.items():
        if not isinstance(key_hex, str) or not _PUBLIC_KEY_HEX.match(key_hex):
            raise CheckpointError(
                "MALFORMED", f"pinned key for {witness_id!r} must be 64 hex chars"
            )
        keys[witness_id] = Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex))
    return keys


def verify_checkpoint(data: Any, pinned: Mapping[str, Ed25519PublicKey]) -> SignedCheckpoint:
    """Parse a checkpoint and check its signature against the pinned keys only."""
    checkpoint = parse_checkpoint(data)
    statement = checkpoint.statement
    key = pinned.get(statement.witness_id)
    if key is None:
        raise CheckpointError(
            "UNPINNED_KEY", f"witness {statement.witness_id!r} is not in the pinned key set"
        )
    try:
        key.verify(checkpoint.signature, statement.signing_bytes())
    except InvalidSignature as exc:
        raise CheckpointError(
            "BAD_SIGNATURE", f"signature by {statement.witness_id!r} does not verify"
        ) from exc
    return checkpoint


def chain_digests(snapshot: Mapping[str, Any]) -> dict[str, list[str]]:
    """Each root's receipt digests in order. Call only on a snapshot that verified."""
    return {
        root: [entry["receipt"]["receipt_digest"] for entry in snapshot["roots"][root]]
        for root in ROOTS
    }


def extension_problem(
    digests: Mapping[str, Sequence[str]], statement: CheckpointStatement
) -> str | None:
    """None if the chains extend the checkpoint, else REGRESSED or FORKED with detail."""
    for root, want in statement.heads().items():
        chain = digests[root]
        if len(chain) < want.length:
            return f"REGRESSED: {root} has {len(chain)} entries, checkpoint covers {want.length}"
        if 0 < want.length <= len(chain) and chain[want.length - 1] != want.head:
            return f"FORKED: {root} entry {want.length - 1} differs from the checkpoint head"
    return None


def _split_view(checkpoints: Sequence[SignedCheckpoint]) -> str | None:
    """Disagreements among the checkpoints themselves, before the snapshot is consulted."""
    heads_at: dict[tuple[str, int], str] = {}
    for checkpoint in checkpoints:
        for root, head in checkpoint.statement.heads().items():
            if head.length == 0:
                continue
            seen = heads_at.setdefault((root, head.length), head.head)
            if seen != head.head:
                return f"SPLIT_VIEW: two checkpoints disagree about {root} at length {head.length}"

    by_witness: dict[str, list[CheckpointStatement]] = {}
    for checkpoint in checkpoints:
        by_witness.setdefault(checkpoint.statement.witness_id, []).append(checkpoint.statement)
    for witness_id, statements in by_witness.items():
        ordered = sorted(statements, key=lambda s: s.checkpoint_seq)
        # Consecutive pairs; the second list is one shorter on purpose.
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if earlier.checkpoint_seq == later.checkpoint_seq and earlier != later:
                return (
                    f"SPLIT_VIEW: witness {witness_id!r} signed two different "
                    f"checkpoints #{later.checkpoint_seq}"
                )
            for root in ROOTS:
                if later.heads()[root].length < earlier.heads()[root].length:
                    return (
                        f"SPLIT_VIEW: witness {witness_id!r} regressed {root} "
                        "between its checkpoints"
                    )
    return None


def custody_report(
    snapshot: Any, checkpoints: Sequence[Any], *, pinned_keys: Mapping[str, str]
) -> CustodyReport:
    """Report how a snapshot stands against signed checkpoints from pinned witnesses.

    ``pinned_keys`` is required and must come from somewhere other than the data
    under test. Any defect refuses; nothing is repaired.
    """
    verdict = verify_snapshot(snapshot)
    if not verdict.ok:
        return _refused(f"SNAPSHOT_INVALID: {verdict.reason}")
    ledger_id = snapshot["ledger_id"]
    digests = chain_digests(snapshot)
    lengths = {root: len(chain) for root, chain in digests.items()}

    try:
        pinned = load_pinned_keys(pinned_keys)
        verified = [verify_checkpoint(data, pinned) for data in checkpoints]
    except CheckpointError as exc:
        return _refused(f"{exc.code}: {exc.detail}", ledger_id)

    for checkpoint in verified:
        if checkpoint.statement.ledger_id != ledger_id:
            return _refused(
                f"MALFORMED: checkpoint is for ledger {checkpoint.statement.ledger_id!r}", ledger_id
            )

    split = _split_view(verified)
    if split is not None:
        return _refused(split + "; freeze; investigate fork or key compromise", ledger_id)

    for checkpoint in verified:
        problem = extension_problem(digests, checkpoint.statement)
        if problem is not None:
            return _refused(
                problem + "; freeze ledger extension; escalate to witnesses and steward", ledger_id
            )

    if not verified:
        return CustodyReport(
            status=UNWITNESSED,
            reason="no checkpoint: history before the first checkpoint cannot be told apart "
            "from a rewrite",
            ledger_id=ledger_id,
            covered={root: 0 for root in ROOTS},
            unwitnessed_entries=dict(lengths),
            freshness="NO_CHECKPOINT",
        )

    covered = {root: max(c.statement.heads()[root].length for c in verified) for root in ROOTS}
    tail = {root: lengths[root] - covered[root] for root in ROOTS}
    total = sum(tail.values())
    witnesses = tuple(sorted({c.statement.witness_id for c in verified}))
    return CustodyReport(
        status=CHECKPOINT_CONSISTENT,
        reason=f"snapshot extends {len(verified)} checkpoint(s) from {len(witnesses)} pinned "
        "witness(es); the witnesses' independence is not established by this check",
        ledger_id=ledger_id,
        witnesses=witnesses,
        corroboration="CORROBORATED" if len(witnesses) >= 2 else "UNCORROBORATED",
        covered=covered,
        unwitnessed_entries=tail,
        freshness="COVERED_TO_HEAD" if total == 0 else f"NO_CHECKPOINT_FOR_LAST_{total}_ENTRIES",
    )
