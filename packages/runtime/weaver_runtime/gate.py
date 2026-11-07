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

Veto policy: a latch in EVALUATING counts as vetoed. The RTL only asserts
``veto_signal`` 68,001 cycles after the trigger, but by then it is already committed to
TRIGGERED, so the gate refuses from the first cycle.

The gate records decisions made by others. It grants no authority itself.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from weaver_contracts.canonical import CanonicalizationError, parse_strict
from weaver_contracts.gate import AuthorizationDecision, GateContractError, Proposal
from weaver_contracts.receipt import Receipt

from .ledger import AdmissionError, LedgerDuplicate, ReceiptLedger
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


class ExecutionContext:
    """Handed to a running action so it can revalidate at checkpoints."""

    def __init__(self, gate: ExecutionGate, proposal: Proposal, expires_at: int) -> None:
        self._gate = gate
        self.proposal = proposal
        self.expires_at = expires_at

    def checkpoint(self) -> None:
        """Recheck the veto, the window, and authority; raise ``GateAbort`` if any failed."""
        self._gate._check_live(self.expires_at, stage="CHECKPOINT")
        self._gate._check_still_authorized(self.proposal, stage="CHECKPOINT")


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
        self, proposal: Proposal, stage: str, reason_code: str, detail: str, status: str
    ) -> GateOutcome:
        receipt = self._ledger.reject(
            "EXECUTION_REFUSED" if status == REJECTED else "EXECUTION_ABORTED",
            {"proposal": proposal.to_dict(), "stage": stage, "detail": detail},
            actor_id=self._gate_id,
            policy_version=self._policy_version,
            reason_code=reason_code,
        )
        return GateOutcome(status=status, reason_code=reason_code, receipt=receipt)

    # ------------------------------------------------------------------ checks

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

        # 1. Observe
        if self._veto.vetoed():
            return self._reject(proposal, "OBSERVE", "VETO_ACTIVE", "veto active", REJECTED)

        # 2. Authorize
        decision = self._ask(proposal)
        if isinstance(decision, str):
            return self._reject(proposal, "AUTHORIZE", "AUTHORIZATION_ERROR", decision, REJECTED)
        if not decision.allowed:
            assert decision.reason_code is not None
            return self._reject(
                proposal, "AUTHORIZE", decision.reason_code, decision.decision_id, REJECTED
            )
        now = self._clock()
        expires_at = min(decision.valid_until, now + self._max_window)
        if expires_at <= now:
            return self._reject(
                proposal, "AUTHORIZE", "WINDOW_EXPIRED", "decision already expired", REJECTED
            )

        # 3. Reserve
        with self._lock:
            if proposal.proposal_id in self._committed:
                refused = "ALREADY_COMMITTED"
            elif proposal.proposal_id in self._reserved:
                refused = "ALREADY_RESERVED"
            else:
                refused = ""
                self._reserved.add(proposal.proposal_id)
        if refused:
            return self._reject(proposal, "RESERVE", refused, proposal.proposal_id, REJECTED)

        try:
            # 4. Execute
            context = ExecutionContext(self, proposal, expires_at)
            try:
                result = action(context)
            except GateAbort as abort:
                return self._reject(proposal, "EXECUTE", abort.reason_code, abort.detail, ABORTED)
            except Exception as exc:
                return self._reject(
                    proposal, "EXECUTE", "EXECUTION_FAILED", type(exc).__name__, ABORTED
                )
            if not isinstance(result, Mapping):
                return self._reject(
                    proposal, "EXECUTE", "EXECUTION_FAILED", "action result is not an object",
                    ABORTED,
                )

            # 5. Revalidate before the irreversible step
            try:
                self._check_live(expires_at, stage="REVALIDATE")
                again = self._check_still_authorized(proposal, stage="REVALIDATE")
            except GateAbort as abort:
                return self._reject(
                    proposal, "REVALIDATE", abort.reason_code, abort.detail, ABORTED
                )

            # 6. Commit
            try:
                receipt = self._ledger.admit(
                    "EXECUTION_COMMITTED",
                    {
                        "proposal": proposal.to_dict(),
                        "decision_id": decision.decision_id,
                        "revalidation_decision_id": again.decision_id,
                        "result": dict(result),
                    },
                    actor_id=self._gate_id,
                    policy_version=self._policy_version,
                    unique_key=f"EXECUTION_COMMITTED:{proposal.proposal_id}",
                )
            except LedgerDuplicate as exc:
                # Another gate (or process) committed this proposal first.
                with self._lock:
                    self._committed.add(proposal.proposal_id)
                return self._reject(proposal, "COMMIT", "ALREADY_COMMITTED", str(exc), ABORTED)
            except AdmissionError as exc:
                return self._reject(proposal, "COMMIT", "RESULT_NOT_RECORDABLE", str(exc), ABORTED)
            with self._lock:
                self._committed.add(proposal.proposal_id)
            return GateOutcome(status=COMMITTED, reason_code=None, receipt=receipt, result=result)
        finally:
            with self._lock:
                self._reserved.discard(proposal.proposal_id)


def _proposal_id_of(event_text: str) -> str | None:
    try:
        event = parse_strict(event_text.encode("utf-8"))
    except CanonicalizationError:
        return None
    proposal = event.get("proposal") if isinstance(event, dict) else None
    value = proposal.get("proposal_id") if isinstance(proposal, dict) else None
    return value if isinstance(value, str) else None
