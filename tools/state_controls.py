"""The nine Step 6 negative controls for wx-runtime-state-1 (WNS-S6-001).

Each control is implemented once, here. ``tests/state/test_state_controls.py`` asserts
the expected outcome of each, and ``tools/state_digest_evidence.py`` records what was
observed. So the evidence report and the tests cannot drift apart.

The demo ledger is built through the real execution gate with fixed clocks, so it is
byte-for-byte reproducible.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import AuthorizationDecision, Proposal
from weaver_contracts.receipt import build
from weaver_runtime.gate import ExecutionGate, TwinVeto
from weaver_runtime.ledger import ReceiptLedger
from weaver_runtime.veto import LuciferLatchTwin
from weaver_verifier.state import (
    ANCHOR_MATCHED,
    DIGEST_SCHEMA,
    REFUSED,
    UNANCHORED,
    compute_digest,
    state_report,
)

LEDGER_ID = "wx-step6-demo"
LEDGER_CLOCK = "2026-11-07T12:00:00Z"
GATE_NOW = 1000


@dataclass(frozen=True)
class ControlResult:
    control: str
    description: str
    expected: str
    observed_status: str
    observed_reason: str
    ok: bool


def _twin() -> LuciferLatchTwin:
    twin = LuciferLatchTwin()
    twin.run(4, rst_n=0, trigger_in=0, threat_level=0)
    twin.run(4, rst_n=1, trigger_in=0, threat_level=0)
    return twin


def build_demo_ledger(path: Path, *, tampered_result: bool = False) -> tuple[dict, dict]:
    """Three commits, one refusal, one abort. Returns (snapshot, anchor).

    With ``tampered_result``, the third commit records a different result. Used to build
    an attacker's fully self-consistent alternative history.
    """

    def authorize(proposal: Proposal) -> AuthorizationDecision:
        if proposal.proposal_id == "p-denied":
            return AuthorizationDecision(
                False, "dec-denied", valid_until=2000, reason_code="DENIED"
            )
        return AuthorizationDecision(True, f"dec-{proposal.proposal_id}", valid_until=2000)

    def staged(result: dict[str, Any]) -> Callable[[Any], dict[str, Any]]:
        return lambda context: result

    def failing(context: Any) -> dict[str, Any]:
        raise RuntimeError("half-done")

    with ReceiptLedger(path, ledger_id=LEDGER_ID, clock=lambda: LEDGER_CLOCK) as ledger:
        gate = ExecutionGate(
            ledger, veto=TwinVeto(_twin()), authorize=authorize, clock=lambda: GATE_NOW
        )
        for pid, value in (("p-1", 1), ("p-2", 2)):
            gate.execute(_proposal(pid, value), staged({"applied": False, "value": value}))
        gate.execute(_proposal("p-denied", 9), staged({"value": 9}))
        gate.execute(_proposal("p-abort", 7), failing)
        third = {"applied": False, "value": 999 if tampered_result else 3}
        gate.execute(_proposal("p-3", 3), staged(third))
        return ledger.snapshot(), ledger.anchor().to_dict()


def _proposal(pid: str, value: int) -> Proposal:
    return Proposal(pid, "agent-7", "SET_CONFIG", "policy-v1", {"key": pid, "value": value})


def _reseal_last_authority(snapshot: dict, event_text: str) -> None:
    entry = snapshot["roots"]["AUTHORITY"][-1]
    entry["event"] = event_text
    receipt = dict(entry["receipt"])
    receipt["event_digest"] = hashlib.sha256(event_text.encode("utf-8")).hexdigest()
    derived = {"schema", "canonicalization", "receipt_digest"}
    body = {k: v for k, v in receipt.items() if k not in derived}
    entry["receipt"] = build(**body).to_dict()


def _result(
    control: str, description: str, expected: str, status: str, reason: str, ok: bool
) -> ControlResult:
    return ControlResult(control, description, expected, status, reason, ok)


def run_controls(workdir: Path) -> list[ControlResult]:
    honest_snapshot, honest_anchor = build_demo_ledger(workdir / "honest.db")
    attacker_snapshot, attacker_anchor = build_demo_ledger(
        workdir / "attacker.db", tampered_result=True
    )
    honest = state_report(honest_snapshot, anchor=honest_anchor)
    if honest.status != ANCHOR_MATCHED or honest.digest is None or honest.state is None:
        raise AssertionError(f"honest baseline did not verify: {honest.reason}")
    results: list[ControlResult] = []

    # 1. Alter an event without updating its hash.
    s = copy.deepcopy(honest_snapshot)
    event = json.loads(s["roots"]["AUTHORITY"][1]["event"])
    event["result"]["value"] = 222
    s["roots"]["AUTHORITY"][1]["event"] = canonicalize(event).decode()
    r = state_report(s, anchor=honest_anchor)
    results.append(_result("C1", "alter an event without updating its hash", "REJECT",
                           r.status, r.reason, r.status == REFUSED and "event digest" in r.reason))

    # 2. Reorder two ledger entries.
    s = copy.deepcopy(honest_snapshot)
    a = s["roots"]["AUTHORITY"]
    a[0], a[1] = a[1], a[0]
    r = state_report(s, anchor=honest_anchor)
    results.append(_result("C2", "reorder two ledger entries", "REJECT",
                           r.status, r.reason, r.status == REFUSED))

    # 3. Truncate the ledger against a trusted external reference.
    s = copy.deepcopy(honest_snapshot)
    del s["roots"]["AUTHORITY"][-1]
    r = state_report(s, anchor=honest_anchor)
    results.append(_result("C3", "truncate against a trusted external anchor", "REJECT",
                           r.status, r.reason, r.status == REFUSED and "truncation" in r.reason))

    # 4. Recompute the entire chain without an external reference.
    r = state_report(attacker_snapshot)
    exposed = (
        r.status == UNANCHORED
        and r.authenticity == "NOT_ESTABLISHED"
        and r.digest != honest.digest
        and state_report(attacker_snapshot, anchor=honest_anchor).status == REFUSED
    )
    results.append(_result("C4", "fully recomputed chain, no external reference",
                           "EXPOSE LIMITATION (UNANCHORED, authenticity not established)",
                           r.status, r.reason, exposed))

    # 5. Change the canonical serialization.
    s = copy.deepcopy(honest_snapshot)
    pretty = json.dumps(json.loads(s["roots"]["AUTHORITY"][-1]["event"]), indent=1)
    _reseal_last_authority(s, pretty)
    r_bytes = state_report(s)
    state = honest.state
    legacy = hashlib.sha256(
        json.dumps({"schema": DIGEST_SCHEMA, "state": state}, sort_keys=True).encode()
    ).hexdigest()
    other_schema = "wx-state-digest-0:" + honest.digest.split(":", 1)[1]
    r_schema = state_report(honest_snapshot, anchor=honest_anchor, expected_digest=other_schema)
    ok5 = (
        r_bytes.status == REFUSED
        and "not WX-CJSON-1 canonical" in r_bytes.reason
        and legacy != honest.digest.split(":", 1)[1]
        and r_schema.status == REFUSED
        and "refusing to reinterpret" in r_schema.reason
    )
    results.append(_result("C5", "change the canonical serialization", "DIGEST MISMATCH / REJECT",
                           r_bytes.status, f"{r_bytes.reason}; other schema: {r_schema.reason}",
                           ok5))

    # 6. Change a committed proposal's outcome (fully resealed).
    s = copy.deepcopy(honest_snapshot)
    event = json.loads(s["roots"]["AUTHORITY"][-1]["event"])
    event["result"]["value"] = 333
    _reseal_last_authority(s, canonicalize(event).decode())
    with_anchor = state_report(s, anchor=honest_anchor)
    with_digest = state_report(s, expected_digest=honest.digest)
    ok6 = with_anchor.status == REFUSED and with_digest.status == REFUSED
    results.append(_result("C6", "change a committed proposal's outcome",
                           "REJECT OR DIGEST MISMATCH", with_anchor.status,
                           f"{with_anchor.reason}; vs digest: {with_digest.reason}", ok6))

    # 7. Present an uncommitted action as committed.
    claim = copy.deepcopy(honest.state)
    claim["executions"]["p-denied"] = dict(claim["executions"]["p-1"])
    r_claim = state_report(honest_snapshot, anchor=honest_anchor, claimed_state=claim)
    s = copy.deepcopy(honest_snapshot)
    s["roots"]["AUTHORITY"].append(s["roots"]["REJECTION"].pop(0))
    r_move = state_report(s)
    ok7 = r_claim.status == REFUSED and r_move.status == REFUSED
    results.append(_result("C7", "present an uncommitted action as committed", "REJECT",
                           r_claim.status, f"{r_claim.reason}; moved entry: {r_move.reason}", ok7))

    # 8. Forged expected digest (and anchor) from the same attacker.
    forged_digest = state_report(attacker_snapshot).digest
    r = state_report(attacker_snapshot, anchor=attacker_anchor, expected_digest=forged_digest)
    ok8 = r.status == ANCHOR_MATCHED and r.custody == "NOT_ESTABLISHED" and r.witness == "W0"
    results.append(_result("C8", "forged expected digest and anchor from the same attacker",
                           "EXPOSE CUSTODY LIMITATION (matches; custody not established)",
                           r.status, r.reason, ok8))

    # 9. Replay the same valid ledger twice (and rebuild it from scratch).
    again = state_report(copy.deepcopy(honest_snapshot), anchor=honest_anchor)
    rebuilt_snapshot, rebuilt_anchor = build_demo_ledger(workdir / "rebuilt.db")
    rebuilt = state_report(rebuilt_snapshot, anchor=rebuilt_anchor)
    ok9 = again.digest == honest.digest == rebuilt.digest
    results.append(_result("C9", "replay the same valid ledger twice", "IDENTICAL DIGEST",
                           again.status, f"digest {again.digest}", ok9))
    return results


def honest_digest(workdir: Path) -> str:
    snapshot, anchor = build_demo_ledger(workdir / "digest.db")
    report = state_report(snapshot, anchor=anchor)
    assert report.digest is not None
    return report.digest


__all__ = ["ControlResult", "build_demo_ledger", "compute_digest", "honest_digest", "run_controls"]
