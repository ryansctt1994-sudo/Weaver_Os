"""A running action or authorizer must not change the proposal the gate authorized.

Before this file, ``Proposal`` was a frozen dataclass whose ``payload`` was still a
plain ``dict``. Code holding the proposal could rewrite it in place, so:

* an action could commit a different payload under the decision issued for the
  original one (the receipt paired ``decision_id`` with a payload it never saw);
* an action could make the proposal un-canonicalizable and then fail, so that
  ``execute()`` raised while recording the refusal and left **no receipt**, while
  the ledger was healthy (WX-EXECUTION-GATE-1: one receipt per call while the
  ledger can record).

``object.__setattr__`` bypasses any frozen dataclass, so the gate also pins the
canonical proposal at entry and records only that pinned copy.
"""

import json

import pytest
from weaver_contracts.gate import AuthorizationDecision, Proposal
from weaver_runtime.gate import ABORTED, COMMITTED, ExecutionGate, TwinVeto

from tests.gate.test_execution_gate import armed_twin
from tests.ledger.helpers import open_ledger


@pytest.fixture()
def ledger(tmp_path):
    led = open_ledger(tmp_path / "integrity.db")
    yield led
    led.close()


class ApprovalById:
    """The common real shape: approval looked up by proposal_id only, recording what it saw."""

    def __init__(self) -> None:
        self.seen: list[dict] = []

    def __call__(self, proposal: Proposal) -> AuthorizationDecision:
        self.seen.append(json.loads(json.dumps(proposal.to_dict())))
        return AuthorizationDecision(True, f"approval-{len(self.seen)}", valid_until=2000)


def gate_for(ledger, authorizer) -> ExecutionGate:
    return ExecutionGate(
        ledger, veto=TwinVeto(armed_twin()), authorize=authorizer, clock=lambda: 1000
    )


def transfer() -> Proposal:
    return Proposal(
        "pay-1", "agent-7", "TRANSFER", "policy-v1",
        {"to": "acct-A", "amount": 10, "memo": {"tags": ["rent"]}},
    )


def recorded(ledger, root: str) -> list[dict]:
    return [json.loads(e["event"]) for e in ledger.snapshot()["roots"][root]]


# --- contract: the payload is read-only ------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.payload.__setitem__("amount", 10_000_000),
        lambda p: p.payload.__delitem__("to"),
        lambda p: p.payload["memo"].__setitem__("tags", []),
        lambda p: p.payload["memo"]["tags"].append("attacker"),
    ],
    ids=["set-top", "delete-top", "set-nested", "append-nested-list"],
)
def test_proposal_payload_cannot_be_mutated_in_place(mutate):
    p = transfer()
    before = p.to_dict()
    with pytest.raises((TypeError, AttributeError)):
        mutate(p)
    assert p.to_dict() == before


def test_read_only_payload_still_reads_like_the_original():
    p = transfer()
    assert p.payload["to"] == "acct-A"
    assert p.payload["memo"]["tags"][0] == "rent"
    assert dict(p.payload)["amount"] == 10
    assert p.to_dict()["payload"] == {"to": "acct-A", "amount": 10, "memo": {"tags": ["rent"]}}
    assert type(p.to_dict()["payload"]["memo"]["tags"]) is list


# --- gate: what commits is what was authorized -----------------------------------


def test_action_rewriting_the_payload_cannot_commit_under_the_original_approval(ledger):
    def action(context):
        context.proposal.payload["amount"] = 10_000_000
        context.proposal.payload["to"] = "acct-ATTACKER"
        return {"staged": True}

    outcome = gate_for(ledger, ApprovalById()).execute(transfer(), action)
    assert outcome.status == ABORTED
    assert recorded(ledger, "AUTHORITY") == []
    [refusal] = recorded(ledger, "REJECTION")
    assert refusal["proposal"]["payload"]["amount"] == 10
    assert refusal["proposal"]["payload"]["to"] == "acct-A"


@pytest.mark.parametrize("field", ["action", "actor_id", "policy_version"])
def test_frozen_field_bypass_by_the_action_aborts_and_records_the_submitted_proposal(
    ledger, field
):
    submitted = transfer().to_dict()

    def action(context):
        object.__setattr__(context.proposal, field, "DELETE_ALL")
        return {"staged": True}

    outcome = gate_for(ledger, ApprovalById()).execute(transfer(), action)
    assert outcome.status == ABORTED
    assert outcome.reason_code == "PROPOSAL_MUTATED"
    assert recorded(ledger, "AUTHORITY") == []
    [refusal] = recorded(ledger, "REJECTION")
    assert refusal["proposal"] == submitted


def test_authorizer_that_rewrites_the_proposal_cannot_change_what_commits(ledger):
    def sneaky(proposal):
        object.__setattr__(proposal, "action", "GRANT_ADMIN")
        return AuthorizationDecision(True, "d-1", valid_until=2000)

    outcome = gate_for(ledger, sneaky).execute(transfer(), lambda c: {"ok": True})
    assert outcome.status != COMMITTED
    assert all(r["proposal"]["action"] == "TRANSFER" for r in recorded(ledger, "REJECTION"))


# --- gate: one receipt per call, even for a poisoned proposal --------------------


@pytest.mark.parametrize(
    "poison", [float("nan"), 1.5, {1, 2}, object()], ids=["nan", "float", "set", "object"]
)
@pytest.mark.parametrize("then", ["raise", "return"])
def test_poisoned_proposal_still_produces_exactly_one_receipt(ledger, poison, then):
    def action(context):
        try:
            context.proposal.payload["amount"] = poison
        except TypeError:
            pass  # read-only payload: fall back to bypassing the frozen dataclass
        object.__setattr__(context.proposal, "actor_id", poison)
        if then == "raise":
            raise RuntimeError("action failed after poisoning")
        return {"staged": True}

    outcome = gate_for(ledger, ApprovalById()).execute(transfer(), action)
    assert outcome.status == ABORTED
    assert (len(recorded(ledger, "AUTHORITY")), len(recorded(ledger, "REJECTION"))) == (0, 1)
    [refusal] = recorded(ledger, "REJECTION")
    assert refusal["proposal"] == transfer().to_dict()


def test_unmodified_proposal_still_commits_and_records_exactly_what_was_authorized(ledger):
    authorizer = ApprovalById()
    outcome = gate_for(ledger, authorizer).execute(transfer(), lambda c: {"staged": True})
    assert outcome.status == COMMITTED
    [commit] = recorded(ledger, "AUTHORITY")
    assert commit["proposal"] == authorizer.seen[0] == transfer().to_dict()
