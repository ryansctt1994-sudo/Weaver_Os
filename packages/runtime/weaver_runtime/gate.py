"""Execution gate: Observe -> Authorize -> Reserve -> Execute -> Revalidate -> Commit.

The TOCTOU model from ``docs/triadic-controls/ARCHITECTURE.md`` (Layer 4), with the
Cathedral ordering (Observe before Authorize) and the Dual Ledger:

1. **Observe.** If the veto is active, refuse before asking anyone for authority.
2. **Authorize.** Ask the injected authorizer. A denial, a malformed answer, or an
   exception all refuse (fail closed).
3. **Reserve.** Open an authority window that ends at the earlier of the decision's
   ``valid_until`` and ``now + max_window``. One live reservation per proposal, and a
   proposal that has already committed cannot run again.
4. **Execute.** Run the caller's action. It *stages* a result and must not apply
   irreversible effects. Long actions call ``context.checkpoint()``, which
   rechecks the veto, the window and authority (the authorizer is asked again), and
   aborts if any of them has failed.
5. **Revalidate.** Immediately before commit: veto still clear, window still open,
   and the authorizer, asked again, still allows with a decision that has not expired.

The authorizer is called at least twice per execution, and once more at every
checkpoint. It must answer "is this proposal authorized right now?" without side
effects. A one-shot verifier, one that consumes a token or records a replay key on each
call as ``CryptoVerifier`` does, cannot be passed in directly: its second answer would be
a replay refusal, so every execution would abort. That fails closed, but such a verifier
needs an adapter that verifies once and then answers revocation and expiry queries.
6. **Commit or safe-abort.** On commit the result is recorded on the Authority Root,
   and that record *is* the commit. Callers apply external effects only after a
   ``COMMITTED`` outcome. Anything else records a receipt on the Rejection Root.

Every call produces exactly one receipt (REJECTIONS_MUST_BE_CHRONICLED).

The gate pins the proposal's canonical form on entry, before the authorizer or the action
runs, and records only that pinned copy. Code holding the proposal object cannot change
what is recorded. If the live proposal no longer matches the pin at a checkpoint or at
revalidation, the run aborts with ``PROPOSAL_MUTATED``.

Veto policy: a latch in EVALUATING counts as vetoed. The RTL only asserts
``veto_signal`` 68,001 cycles after the trigger, but by then it is already committed to
TRIGGERED, so the gate refuses from the first cycle.

The gate records decisions made by others. It grants no authority itself.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from weaver_contracts.canonical import CanonicalizationError, canonicalize, parse_strict
from weaver_contracts.gate import AuthorizationDecision, GateContractError, Proposal
from weaver_contracts.receipt import Receipt

from .ledger import AdmissionError, CommitRefused, LedgerDuplicate, ReceiptLedger
from .veto import STATE_ARMED, LuciferLatchTwin

COMMITTED = "COMMITTED"
REJECTED = "REJECTED"
ABORTED = "ABORTED"


class VetoSource(Protocol):
    def vetoed(self) -> bool: ...


class TwinVeto:
    """Veto view of a ``LuciferLatchTwin``: anything other than ARMED is a veto."""

    def __init__(self, twin: LuciferLatchTwin) -> None:
        self._twin = twin

    def vetoed(self) -> bool:
        return self._twin.current_state != STATE_ARMED or self._twin.veto_signal == 1


VETO_CONTROL = "veto"


def revocation_control(proposal_id: str) -> str:
    """Name of the ledger control that records a revocation of one proposal's authority."""
    return f"revoked:{proposal_id}"


class GateAbort(Exception):
    """Raised by ``ExecutionContext.checkpoint`` to stop a running action."""

    def __init__(self, reason_code: str, detail: str) -> None:
        super().__init__(detail)
        self.reason_code = reason_code
        self.detail = detail


@dataclass(frozen=True)
class GateOutcome:
    status: str
    reason_code: str | None
    receipt: Receipt
    result: Mapping[str, Any] | None = None


Authorizer = Callable[[Proposal], AuthorizationDecision]
Action = Callable[["ExecutionContext"], Mapping[str, Any]]


@dataclass(frozen=True)
class _Pinned:
    """The proposal as submitted: its canonical bytes and its validated id."""

    canonical: bytes
    proposal_id: str

    def record(self) -> dict[str, Any]:
        """A new plain copy for a ledger event; nothing downstream can alias the pin."""
        copy: dict[str, Any] = parse_strict(self.canonical)
        return copy


def _pin(proposal: Proposal) -> _Pinned:
    """Canonicalize the proposal once and re-check every field against the contract."""
    try:
        checked = Proposal(**parse_strict(canonicalize(proposal.to_dict())))
    except (CanonicalizationError, TypeError, ValueError, KeyError) as exc:
        raise GateContractError(f"proposal is outside the contract on entry: {exc}") from exc
    return _Pinned(canonical=canonicalize(checked.to_dict()), proposal_id=checked.proposal_id)


def _canonical_or_none(proposal: Proposal) -> bytes | None:
    try:
        return canonicalize(proposal.to_dict())
    except Exception:  # any failure means it no longer matches the pin
        return None


class ExecutionContext:
    """Handed to a running action so it can revalidate at checkpoints."""

    def __init__(
        self, gate: ExecutionGate, proposal: Proposal, expires_at: int, pinned: _Pinned
    ) -> None:
        self._gate = gate
        self.proposal = proposal
        self.expires_at = expires_at
        self._pinned = pinned

    def checkpoint(self) -> None:
        """Recheck the proposal, the veto, the window, and authority; raise ``GateAbort``."""
        self._gate._check_unchanged(self.proposal, self._pinned, stage="CHECKPOINT")
        self._gate._check_live(self.expires_at, stage="CHECKPOINT")
        self._gate._check_still_authorized(self.proposal, stage="CHECKPOINT")
        self._gate._check_unchanged(self.proposal, self._pinned, stage="CHECKPOINT")


class ExecutionGate:
    def __init__(
        self,
        ledger: ReceiptLedger,
        *,
        veto: VetoSource,
        authorize: Authorizer,
        gate_id: str = "execution-gate",
        policy_version: str = "gate-policy-v1",
        max_window: int = 300,
        clock: Callable[[], int] = lambda: int(time.time()),
        atomic_effect: Callable[
            [sqlite3.Connection, Mapping[str, Any], Mapping[str, Any]], None
        ] | None = None,
    ) -> None:
        if not isinstance(max_window, int) or max_window < 1:
            raise ValueError("max_window must be a positive integer")
        self._ledger = ledger
        self._veto = veto
        self._authorize = authorize
        self._gate_id = gate_id
        self._policy_version = policy_version
        self._max_window = max_window
        self._clock = clock
        # Installed by a trusted resource owner, never accepted per execute() call.
        self._atomic_effect = atomic_effect
        self._lock = threading.Lock()
        self._reserved: set[str] = set()
        # Proposals already committed in this ledger may not run again, even across restarts.
        self._committed: set[str] = set()
        for entry in ledger.snapshot()["roots"]["AUTHORITY"]:
            if entry["receipt"]["event_type"] == "EXECUTION_COMMITTED":
                proposal_id = _proposal_id_of(entry["event"])
                if proposal_id is not None:
                    self._committed.add(proposal_id)

    # ----------------------------------------------------------------- records

    def _reject(
        self, pinned: _Pinned, stage: str, reason_code: str, detail: str, status: str
    ) -> GateOutcome:
        receipt = self._ledger.reject(
            "EXECUTION_REFUSED" if status == REJECTED else "EXECUTION_ABORTED",
            {"proposal": pinned.record(), "stage": stage, "detail": detail},
            actor_id=self._gate_id,
            policy_version=self._policy_version,
            reason_code=reason_code,
        )
        return GateOutcome(status=status, reason_code=reason_code, receipt=receipt)

    # ------------------------------------------------------------------ checks

    def _ledger_guard(self, proposal_id: str) -> Callable[[sqlite3.Connection], None]:
        """Authoritative veto and revocation check, run inside the commit transaction.

        It reads ledger-recorded controls after ``BEGIN IMMEDIATE`` and before the append,
        so a control change either committed before this transaction (and is seen) or
        waits for it (and is ordered after the commit). The in-memory veto source is not
        consulted here. Only what the ledger records counts.
        """
        revocation = revocation_control(proposal_id)

        def guard(conn: sqlite3.Connection) -> None:
            for name, refused_value, reason in (
                (VETO_CONTROL, "active", "VETO_RECORDED_BEFORE_COMMIT"),
                (revocation, "revoked", "REVOKED_RECORDED_BEFORE_COMMIT"),
            ):
                row = conn.execute("SELECT value FROM controls WHERE name = ?", (name,)).fetchone()
                if row is not None and row[0] == refused_value:
                    raise CommitRefused(reason, f"control {name} is {refused_value} in the ledger")

        return guard

    def _check_unchanged(self, proposal: Proposal, pinned: _Pinned, *, stage: str) -> None:
        if _canonical_or_none(proposal) != pinned.canonical:
            raise GateAbort("PROPOSAL_MUTATED", f"proposal changed after entry, seen at {stage}")

    def _check_live(self, expires_at: int, *, stage: str) -> None:
        if self._veto.vetoed():
            raise GateAbort("VETO_DURING_EXECUTION", f"veto active at {stage}")
        if self._clock() >= expires_at:
            raise GateAbort("WINDOW_EXPIRED", f"authority window closed at {stage}")

    def _check_still_authorized(self, proposal: Proposal, *, stage: str) -> AuthorizationDecision:
        again = self._ask(proposal)
        if isinstance(again, str) or not again.allowed:
            detail = again if isinstance(again, str) else again.decision_id
            raise GateAbort("REVALIDATION_DENIED", f"{stage}: {detail}")
        if again.valid_until <= self._clock():
            raise GateAbort("WINDOW_EXPIRED", f"{stage}: re-issued decision already expired")
        return again

    def _ask(self, proposal: Proposal) -> AuthorizationDecision | str:
        try:
            decision = self._authorize(proposal)
        except Exception as exc:  # fail closed on any authorizer failure
            return f"authorizer raised {type(exc).__name__}"
        if not isinstance(decision, AuthorizationDecision):
            return "authorizer returned something other than an AuthorizationDecision"
        return decision

    # ----------------------------------------------------------------- execute

    def execute(self, proposal: Proposal, action: Action) -> GateOutcome:
        if not isinstance(proposal, Proposal):
            raise GateContractError("execute() takes a Proposal")
        # 0. Pin the proposal before the authorizer or the action sees it. Every receipt
        #    records this copy, and every id below comes from it, not the live object.
        pinned = _pin(proposal)
        pid = pinned.proposal_id

        # 1. Observe
        if self._veto.vetoed():
            return self._reject(pinned, "OBSERVE", "VETO_ACTIVE", "veto active", REJECTED)

        # 2. Authorize
        decision = self._ask(proposal)
        if isinstance(decision, str):
            return self._reject(pinned, "AUTHORIZE", "AUTHORIZATION_ERROR", decision, REJECTED)
        try:
            self._check_unchanged(proposal, pinned, stage="AUTHORIZE")
        except GateAbort as abort:
            return self._reject(pinned, "AUTHORIZE", abort.reason_code, abort.detail, REJECTED)
        if not decision.allowed:
            assert decision.reason_code is not None
            return self._reject(
                pinned, "AUTHORIZE", decision.reason_code, decision.decision_id, REJECTED
            )
        now = self._clock()
        expires_at = min(decision.valid_until, now + self._max_window)
        if expires_at <= now:
            return self._reject(
                pinned, "AUTHORIZE", "WINDOW_EXPIRED", "decision already expired", REJECTED
            )

        # 3. Reserve
        with self._lock:
            if pid in self._committed:
                refused = "ALREADY_COMMITTED"
            elif pid in self._reserved:
                refused = "ALREADY_RESERVED"
            else:
                refused = ""
                self._reserved.add(pid)
        if refused:
            return self._reject(pinned, "RESERVE", refused, pid, REJECTED)

        try:
            # 4. Execute
            context = ExecutionContext(self, proposal, expires_at, pinned)
            try:
                result = action(context)
            except GateAbort as abort:
                return self._reject(pinned, "EXECUTE", abort.reason_code, abort.detail, ABORTED)
            except Exception as exc:
                return self._reject(
                    pinned, "EXECUTE", "EXECUTION_FAILED", type(exc).__name__, ABORTED
                )
            if not isinstance(result, Mapping):
                return self._reject(
                    pinned, "EXECUTE", "EXECUTION_FAILED", "action result is not an object",
                    ABORTED,
                )

            # 5. Revalidate before the irreversible step. The proposal is checked against
            #    the pin before the authorizer is asked again and after it answers.
            try:
                self._check_unchanged(proposal, pinned, stage="REVALIDATE")
                self._check_live(expires_at, stage="REVALIDATE")
                again = self._check_still_authorized(proposal, stage="REVALIDATE")
                self._check_unchanged(proposal, pinned, stage="REVALIDATE")
            except GateAbort as abort:
                return self._reject(
                    pinned, "REVALIDATE", abort.reason_code, abort.detail, ABORTED
                )

            # 6. Commit. If a trusted owner installed an effect callback, the
            # resource effect and receipt must both commit in ONE SQLite transaction.
            # This is an application-side atomicity property, not OS confinement.
            try:
                committed_result = parse_strict(canonicalize(dict(result)))
            except (CanonicalizationError, ValueError, TypeError) as exc:
                return self._reject(
                    pinned, "COMMIT", "RESULT_NOT_RECORDABLE", type(exc).__name__, ABORTED
                )

            def commit_guard(conn: sqlite3.Connection) -> None:
                self._ledger_guard(pid)(conn)
                if self._atomic_effect is not None:
                    try:
                        # Detached canonical copies avoid handing owner code the live
                        # proposal object or a mutable uncommitted event alias.
                        self._atomic_effect(
                            conn, pinned.record(), parse_strict(canonicalize(committed_result))
                        )
                    except CommitRefused:
                        raise
                    except Exception as exc:
                        raise CommitRefused("EFFECT_WRITE_FAILED", type(exc).__name__) from exc

            try:
                receipt = self._ledger.admit(
                    "EXECUTION_COMMITTED",
                    {
                        "proposal": pinned.record(),
                        "decision_id": decision.decision_id,
                        "revalidation_decision_id": again.decision_id,
                        "result": committed_result,
                    },
                    actor_id=self._gate_id,
                    policy_version=self._policy_version,
                    unique_key=f"EXECUTION_COMMITTED:{pid}",
                    guard=commit_guard,
                )
            except CommitRefused as exc:
                # A veto or revocation recorded in the ledger before the commit's
                # serialization point. Nothing was written.
                return self._reject(pinned, "COMMIT", exc.reason_code, exc.detail, ABORTED)
            except LedgerDuplicate as exc:
                # Another gate (or process) committed this proposal first.
                with self._lock:
                    self._committed.add(pid)
                return self._reject(pinned, "COMMIT", "ALREADY_COMMITTED", str(exc), ABORTED)
            except AdmissionError as exc:
                return self._reject(pinned, "COMMIT", "RESULT_NOT_RECORDABLE", str(exc), ABORTED)
            with self._lock:
                self._committed.add(pid)
            return GateOutcome(
                status=COMMITTED, reason_code=None, receipt=receipt, result=committed_result
            )
        finally:
            with self._lock:
                self._reserved.discard(pid)


def _proposal_id_of(event_text: str) -> str | None:
    try:
        event = parse_strict(event_text.encode("utf-8"))
    except CanonicalizationError:
        return None
    proposal = event.get("proposal") if isinstance(event, dict) else None
    value = proposal.get("proposal_id") if isinstance(proposal, dict) else None
    return value if isinstance(value, str) else None
