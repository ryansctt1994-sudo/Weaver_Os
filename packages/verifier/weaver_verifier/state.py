"""Runtime-state reconstruction and digest from a ReceiptLedger snapshot (Step 6).

Projection ``wx-runtime-state-1``: the set of executions committed by the execution
gate, rebuilt **only** from a snapshot that passes ``verify_snapshot``. Rejected and
quarantined attempts are evidence, not state (FAILED_ACTIONS_ARE_NOT_STATE), so they
do not enter the projection. The Rejection Root still enters the digest, through its
head and length.

This is a new, separately named projection. It does not replace or reinterpret
``authority-transition-reducer-v1`` (the local reducer over ``authority_ledger.json``) or
the Witness RC1 adapter, and it does not touch ``published_manifest.json``.
E3.5 stays withheld.

Digest ``wx-state-digest-1``:

    "wx-state-digest-1:" + hex(SHA-256(b"wx-state-digest-1\\x00" + WX-CJSON-1({
        schema, projection, canonicalization,
        source:  {kind: "reducer_module_sha256", value: SHA-256 of this file},
        ledger:  {ledger_id, chronicle_root, roots: {AUTHORITY, REJECTION}: {length, head}},
        state:   <reconstructed state>,
    })))

The digest names its own version, so a digest made under another schema is refused,
never reinterpreted. Nothing in it comes from a caller's assertion: the state is
reconstructed, the ledger heads are recomputed by the verifier, and the source hash is
read from this module's own bytes.

What a status means:

- ``REFUSED``: the history or the claim is not supported. A reason is given.
- ``UNANCHORED``: the chains are internally consistent. **Authenticity is not
  established.** A complete rewrite with every digest recomputed looks the same.
- ``ANCHOR_MATCHED``: also matches the supplied anchor. **Custody is not established.**
  If the party that produced the ledger also produced the anchor (or the expected
  digest), a match proves nothing more than ``UNANCHORED``.

There is deliberately no status meaning "witnessed" or "authentic". Matching digests are
not independent witnessing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict
from weaver_contracts.ledger import ROOTS

from .ledger import verify_snapshot

DIGEST_SCHEMA = "wx-state-digest-1"
PROJECTION = "wx-runtime-state-1"
CANONICALIZATION = "WX-CJSON-1"
REDUCER_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

REFUSED = "REFUSED"
UNANCHORED = "UNANCHORED"
ANCHOR_MATCHED = "ANCHOR_MATCHED"

_PROPOSAL_FIELDS = frozenset({"proposal_id", "actor_id", "action", "policy_version", "payload"})
_COMMIT_FIELDS = frozenset({"proposal", "decision_id", "revalidation_decision_id", "result"})
SUPPORTED_AUTHORITY_EVENTS = frozenset({"EXECUTION_COMMITTED"})


class StateRefused(ValueError):
    """The snapshot cannot be reduced to wx-runtime-state-1."""


@dataclass(frozen=True)
class StateReport:
    status: str
    reason: str
    digest: str | None
    state: dict[str, Any] | None
    authenticity: str = "NOT_ESTABLISHED"
    custody: str = "NOT_ESTABLISHED"
    witness: str = "W0"

    @property
    def supported(self) -> bool:
        return self.status != REFUSED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _refused(reason: str) -> StateReport:
    return StateReport(status=REFUSED, reason=reason, digest=None, state=None)


def _sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonicalize(value)).hexdigest()


def reconstruct(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce the Authority Root of an already verified snapshot to the projection.

    Call ``state_report`` rather than this directly: it verifies the chains first.
    """
    executions: dict[str, Any] = {}
    for index, entry in enumerate(snapshot["roots"]["AUTHORITY"]):
        receipt = entry["receipt"]
        where = f"AUTHORITY[{index}]"
        if receipt["event_type"] not in SUPPORTED_AUTHORITY_EVENTS:
            raise StateRefused(f"{where}: unsupported event type {receipt['event_type']}")
        try:
            event = parse_strict(entry["event"].encode("utf-8"))
        except CanonicalizationError as exc:
            raise StateRefused(f"{where}: event is not WX-CJSON-1: {exc}") from exc
        if not isinstance(event, dict) or set(event) != _COMMIT_FIELDS:
            raise StateRefused(f"{where}: commit event must have exactly {sorted(_COMMIT_FIELDS)}")
        proposal = event["proposal"]
        if not isinstance(proposal, dict) or set(proposal) != _PROPOSAL_FIELDS:
            raise StateRefused(f"{where}: proposal must have exactly {sorted(_PROPOSAL_FIELDS)}")
        proposal_id = proposal["proposal_id"]
        if not isinstance(proposal_id, str) or not proposal_id:
            raise StateRefused(f"{where}: proposal_id must be a non-empty string")
        if proposal_id in executions:
            raise StateRefused(f"{where}: proposal {proposal_id!r} committed twice")
        executions[proposal_id] = {
            "action": proposal["action"],
            "actor_id": proposal["actor_id"],
            "policy_version": proposal["policy_version"],
            "payload_sha256": _sha256_canonical(proposal["payload"]),
            "decision_id": event["decision_id"],
            "revalidation_decision_id": event["revalidation_decision_id"],
            "result_sha256": _sha256_canonical(event["result"]),
            "sequence": receipt["sequence"],
            "receipt_digest": receipt["receipt_digest"],
        }
    return {"projection": PROJECTION, "executions": executions}


def compute_digest(
    ledger_id: str, chronicle_root: str, heads: Mapping[str, Mapping[str, Any]], state: Any
) -> str:
    preimage = {
        "schema": DIGEST_SCHEMA,
        "projection": PROJECTION,
        "canonicalization": CANONICALIZATION,
        "source": {"kind": "reducer_module_sha256", "value": REDUCER_SOURCE_SHA256},
        "ledger": {
            "ledger_id": ledger_id,
            "chronicle_root": chronicle_root,
            "roots": {root: dict(heads[root]) for root in ROOTS},
        },
        "state": state,
    }
    body = DIGEST_SCHEMA.encode("ascii") + b"\x00" + canonicalize(preimage)
    return f"{DIGEST_SCHEMA}:{hashlib.sha256(body).hexdigest()}"


def _heads(snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    heads = {}
    for root in ROOTS:
        entries = snapshot["roots"][root]
        head = entries[-1]["receipt"]["receipt_digest"] if entries else "0" * 64
        heads[root] = {"length": len(entries), "head": head}
    return heads


def state_report(
    snapshot: Any,
    *,
    anchor: Any = None,
    expected_digest: str | None = None,
    claimed_state: Any = None,
) -> StateReport:
    """Reconstruct, digest, and check a snapshot. Never trusts the caller's digest or state.

    ``expected_digest`` and ``claimed_state`` are compared with what is reconstructed.
    They are never used to produce the result.
    """
    if expected_digest is not None and (
        not isinstance(expected_digest, str)
        or not expected_digest.startswith(f"{DIGEST_SCHEMA}:")
    ):
        return _refused(
            f"expected digest is not a {DIGEST_SCHEMA} digest; refusing to reinterpret it"
        )
    verdict = verify_snapshot(snapshot, anchor=anchor)
    if not verdict.ok:
        return _refused(f"history rejected: {verdict.reason}")
    assert verdict.chronicle_root is not None
    try:
        state = reconstruct(snapshot)
    except StateRefused as exc:
        return _refused(f"state not reconstructable: {exc}")
    digest = compute_digest(snapshot["ledger_id"], verdict.chronicle_root, _heads(snapshot), state)
    if claimed_state is not None:
        try:
            claimed = canonicalize(claimed_state)
        except CanonicalizationError:
            return _refused("claimed state is not canonicalizable")
        if claimed != canonicalize(state):
            return _refused("claimed state is not supported by the ledger")
    if expected_digest is not None and expected_digest != digest:
        return _refused("digest mismatch: the ledger does not reproduce the expected digest")
    if verdict.anchored:
        return StateReport(
            status=ANCHOR_MATCHED,
            reason="history matches the supplied anchor; the anchor's custody is not checked",
            digest=digest,
            state=state,
        )
    return StateReport(
        status=UNANCHORED,
        reason="chains internally consistent; without an external anchor a full rewrite "
        "is indistinguishable from authentic history",
        digest=digest,
        state=state,
    )


def main(argv: list[str] | None = None) -> int:
    """Fresh-process verification: ``python -m weaver_verifier.state --snapshot FILE``."""
    parser = argparse.ArgumentParser(description="Reconstruct and digest wx-runtime-state-1")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--anchor", type=Path)
    parser.add_argument("--expect")
    parser.add_argument("--claim", type=Path)
    args = parser.parse_args(argv)
    try:
        snapshot = parse_strict(args.snapshot.read_bytes())
        anchor = parse_strict(args.anchor.read_bytes()) if args.anchor else None
        claim = parse_strict(args.claim.read_bytes()) if args.claim else None
    except (OSError, CanonicalizationError) as exc:
        print(canonicalize(_refused(f"input unreadable: {exc}").to_dict()).decode())
        return 1
    report = state_report(snapshot, anchor=anchor, expected_digest=args.expect, claimed_state=claim)
    output = {"reducer_source_sha256": REDUCER_SOURCE_SHA256, **report.to_dict()}
    print(canonicalize(output).decode())
    return 0 if report.supported else 1


if __name__ == "__main__":
    sys.exit(main())
