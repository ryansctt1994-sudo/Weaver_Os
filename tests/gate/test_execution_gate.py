"""Execution gate: each TOCTOU stage, fail-closed paths, and one receipt per call."""

import threading

import pytest
from weaver_contracts.gate import AuthorizationDecision, GateContractError, Proposal
from weaver_runtime.gate import (
    ABORTED,
    COMMITTED,
    REJECTED,
    ExecutionGate,
    TwinVeto,
)
from weaver_runtime.ledger import LedgerBusy
from weaver_runtime.veto import LuciferLatchTwin
from weaver_verifier.ledger import verify_snapshot

from tests.ledger.helpers import open_ledger


class Clock:
    def __init__(self, now: int = 1000) -> None:
        self.now = now

    def __call__(self) -> int:
        return self.now


class Authorizer:
    """Scripted authorizer that counts calls."""

    def __init__(self, *answers) -> None:
        self.answers = list(answers) or ["allow"]
        self.calls = 0

    def __call__(self, proposal):
        answer = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        if isinstance(answer, Exception):
            raise answer
        if answer == "allow":
            return AuthorizationDecision(True, f"dec-{self.calls}", valid_until=2000)
        if isinstance(answer, tuple):  # ("allow", valid_until)
            return AuthorizationDecision(True, f"dec-{self.calls}", valid_until=answer[1])
        if answer == "garbage":
            return {"allowed": True}
        return AuthorizationDecision(
            False, f"dec-{self.calls}", valid_until=2000, reason_code=answer
        )


def armed_twin() -> LuciferLatchTwin:
    twin = LuciferLatchTwin()
    twin.run(4, rst_n=0, trigger_in=0, threat_level=0)
    twin.run(4, rst_n=1, trigger_in=0, threat_level=0)
    return twin


def proposal(pid="prop-1", payload=None) -> Proposal:
    return Proposal(pid, "agent-7", "SET_CONFIG", "policy-v1", payload or {"key": "a", "value": 1})


@pytest.fixture()
def env(tmp_path):
    ledger = open_ledger(tmp_path / "gate.db")
    twin = armed_twin()
    clock = Clock()
    yield ledger, twin, clock
    ledger.close()


def make_gate(env, authorizer, **kwargs):
    ledger, twin, clock = env
    return ExecutionGate(ledger, veto=TwinVeto(twin), authorize=authorizer, clock=clock, **kwargs)


def roots(env):
    snapshot = env[0].snapshot()
    return len(snapshot["roots"]["AUTHORITY"]), len(snapshot["roots"]["REJECTION"])


def staged(result=None):
    calls = []

    def action(context):
        calls.append(context.proposal.proposal_id)
        return result if result is not None else {"applied": False, "staged": "config-diff"}

    action.calls = calls
    return action


# --- happy path ---------------------------------------------------------------


def test_commit_records_on_the_authority_root_only(env):
    authorizer = Authorizer("allow")
    outcome = make_gate(env, authorizer).execute(proposal(), staged())
    assert outcome.status == COMMITTED and outcome.reason_code is None
    assert outcome.receipt.root == "AUTHORITY"
    assert outcome.receipt.event_type == "EXECUTION_COMMITTED"
    assert authorizer.calls == 2  # authorize + revalidate
    assert roots(env) == (1, 0)
    assert verify_snapshot(env[0].snapshot()).ok


# --- refusals before execution --------------------------------------------------


def test_observe_comes_before_authorize(env):
    _, twin, _ = env
    twin.run(1, rst_n=1, trigger_in=1, threat_level=0)  # EVALUATING; RTL veto not yet asserted
    assert twin.veto_signal == 0
    authorizer, action = Authorizer("allow"), staged()
    outcome = make_gate(env, authorizer).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (REJECTED, "VETO_ACTIVE")
    assert authorizer.calls == 0 and action.calls == []
    assert roots(env) == (0, 1)


def test_triggered_latch_refuses(env):
    _, twin, _ = env
    twin.run(1, rst_n=1, trigger_in=1, threat_level=0)
    twin.run(68001, rst_n=1, trigger_in=0, threat_level=0)
    assert twin.veto_signal == 1
    assert make_gate(env, Authorizer()).execute(proposal(), staged()).reason_code == "VETO_ACTIVE"


@pytest.mark.parametrize(
    "answer, reason",
    [
        ("POLICY_DENIED", "POLICY_DENIED"),
        (RuntimeError("boom"), "AUTHORIZATION_ERROR"),
        ("garbage", "AUTHORIZATION_ERROR"),
    ],
)
def test_authorization_failures_refuse_without_executing(env, answer, reason):
    action = staged()
    outcome = make_gate(env, Authorizer(answer)).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (REJECTED, reason)
    assert action.calls == []
    assert roots(env) == (0, 1)


def test_already_expired_decision_refuses(env):
    env[2].now = 2000
    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), staged())
    assert (outcome.status, outcome.reason_code) == (REJECTED, "WINDOW_EXPIRED")


def test_window_is_capped_by_max_window(env):
    seen = {}

    def action(context):
        seen["expires_at"] = context.expires_at
        return {}

    make_gate(env, Authorizer("allow"), max_window=30).execute(proposal(), action)
    assert seen["expires_at"] == 1030


# --- aborts during and after execution ---------------------------------------


def test_action_exception_aborts(env):
    def action(context):
        raise ValueError("half-done")

    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (ABORTED, "EXECUTION_FAILED")
    assert roots(env) == (0, 1)


def test_veto_tripping_during_execution_aborts_before_commit(env):
    _, twin, _ = env

    def action(context):
        twin.run(1, rst_n=1, trigger_in=0, threat_level=255)  # threat rises mid-action
        return {"staged": True}

    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (ABORTED, "VETO_DURING_EXECUTION")
    assert roots(env) == (0, 1)


def test_checkpoint_stops_a_long_action_midway(env):
    _, twin, _ = env
    steps = []

    def action(context):
        for step in range(5):
            if step == 2:
                twin.run(1, rst_n=1, trigger_in=1, threat_level=0)
            context.checkpoint()
            steps.append(step)
        return {}

    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (ABORTED, "VETO_DURING_EXECUTION")
    assert steps == [0, 1]


def test_window_expiring_during_execution_aborts(env):
    clock = env[2]

    def action(context):
        clock.now = 2000
        return {}

    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (ABORTED, "WINDOW_EXPIRED")


@pytest.mark.parametrize("second", ["REVOKED", RuntimeError("down"), "garbage"])
def test_revocation_between_authorize_and_commit_aborts(env, second):
    outcome = make_gate(env, Authorizer("allow", second)).execute(proposal(), staged())
    assert (outcome.status, outcome.reason_code) == (ABORTED, "REVALIDATION_DENIED")
    assert roots(env) == (0, 1)


def test_revocation_mid_action_is_caught_at_the_next_checkpoint(env):
    steps = []

    def action(context):
        for step in range(5):
            context.checkpoint()
            steps.append(step)
        return {}

    authorizer = Authorizer("allow", "allow", "REVOKED")
    outcome = make_gate(env, authorizer).execute(proposal(), action)
    assert (outcome.status, outcome.reason_code) == (ABORTED, "REVALIDATION_DENIED")
    assert steps == [0]
    event = env[0].snapshot()["roots"]["REJECTION"][0]["event"]
    assert '"detail":"CHECKPOINT: dec-3"' in event
    assert roots(env) == (0, 1)


def test_reissued_decision_that_has_already_expired_aborts(env):
    """First decision valid until t=2000, re-issued one only until t=999, clock at t=1000."""
    outcome = make_gate(env, Authorizer("allow", ("allow", 999))).execute(proposal(), staged())
    assert (outcome.status, outcome.reason_code) == (ABORTED, "WINDOW_EXPIRED")
    assert roots(env) == (0, 1)


def test_one_shot_authorizer_cannot_commit(env):
    """An authorizer that refuses its second call (replay-consuming) fails closed."""
    outcome = make_gate(env, Authorizer("allow", "REPLAY_DETECTED")).execute(proposal(), staged())
    assert (outcome.status, outcome.reason_code) == (ABORTED, "REVALIDATION_DENIED")
    assert roots(env) == (0, 1)


def test_unrecordable_result_aborts(env):
    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), staged({"ratio": 0.5}))
    assert (outcome.status, outcome.reason_code) == (ABORTED, "RESULT_NOT_RECORDABLE")
    assert roots(env) == (0, 1)


def test_non_mapping_result_aborts(env):
    outcome = make_gate(env, Authorizer("allow")).execute(proposal(), lambda c: ["not", "a", "map"])
    assert (outcome.status, outcome.reason_code) == (ABORTED, "EXECUTION_FAILED")


# --- replay and duplicates -----------------------------------------------------


def test_committed_proposal_cannot_run_again_even_after_restart(env, tmp_path):
    ledger = env[0]
    assert make_gate(env, Authorizer()).execute(proposal(), staged()).status == COMMITTED
    again = make_gate(env, Authorizer()).execute(proposal(), staged())
    assert (again.status, again.reason_code) == (REJECTED, "ALREADY_COMMITTED")
    ledger.close()
    with open_ledger(tmp_path / "gate.db") as reopened:
        fresh = ExecutionGate(
            reopened, veto=TwinVeto(env[1]), authorize=Authorizer(), clock=env[2]
        ).execute(proposal(), staged())
    assert fresh.reason_code == "ALREADY_COMMITTED"


def test_concurrent_execution_of_the_same_proposal_is_refused(env):
    gate = make_gate(env, Authorizer())
    inside, release = threading.Event(), threading.Event()
    results = {}

    def slow(context):
        inside.set()
        release.wait(timeout=10)
        return {}

    first = threading.Thread(target=lambda: results.setdefault("a", gate.execute(proposal(), slow)))
    first.start()
    assert inside.wait(timeout=10)
    results["b"] = gate.execute(proposal(), staged())
    release.set()
    first.join(timeout=10)
    assert results["b"].reason_code == "ALREADY_RESERVED"
    assert results["a"].status == COMMITTED


def test_failed_run_releases_its_reservation(env):
    gate = make_gate(env, Authorizer("allow", "REVOKED", "allow"))
    assert gate.execute(proposal(), staged()).status == ABORTED
    assert gate.execute(proposal(), staged()).status == COMMITTED


# --- invariants -----------------------------------------------------------------


def test_every_call_produces_exactly_one_receipt(env):
    _, twin, clock = env
    gate = make_gate(env, Authorizer("allow", "allow", "NO", "allow", "REVOKED"))
    outcomes = [
        gate.execute(proposal("p1"), staged()),
        gate.execute(proposal("p2"), staged()),
        gate.execute(proposal("p3"), lambda c: (_ for _ in ()).throw(KeyError("x"))),
        gate.execute(proposal("p1"), staged()),
    ]
    twin.run(1, rst_n=1, trigger_in=1, threat_level=0)
    outcomes.append(gate.execute(proposal("p4"), staged()))
    authority, rejection = roots(env)
    assert authority + rejection == len(outcomes)
    assert authority == sum(o.status == COMMITTED for o in outcomes)
    for outcome in outcomes:
        assert outcome.receipt.root == ("AUTHORITY" if outcome.status == COMMITTED else "REJECTION")
    assert verify_snapshot(env[0].snapshot(), anchor=env[0].anchor().to_dict()).ok


def test_proposal_payload_is_copied_on_construction():
    payload = {"value": 1}
    p = proposal(payload=payload)
    payload["value"] = 999
    assert p.to_dict()["payload"] == {"value": 1}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"proposal_id": "TBD"},
        {"action": "lower"},
        {"payload": {"x": 1.5}},
        {"payload": ["list"]},
    ],
)
def test_malformed_proposals_are_rejected(kwargs):
    base = {
        "proposal_id": "p",
        "actor_id": "a",
        "action": "DO",
        "policy_version": "v1",
        "payload": {},
    }
    base.update(kwargs)
    with pytest.raises(GateContractError):
        Proposal(**base)


@pytest.mark.parametrize(
    "args",
    [
        (True, "d1", 10, "WHY"),
        (False, "d1", 10, None),
        (True, "d1", -1, None),
        ("yes", "d1", 10, None),
    ],
)
def test_malformed_decisions_are_rejected(args):
    with pytest.raises(GateContractError):
        AuthorizationDecision(*args)


# --- review follow-ups: multiple gates, commit boundary, ledger failure --------


def test_two_gates_sharing_a_ledger_cannot_both_commit(tmp_path):
    """Each gate's in-memory guards are local; the ledger's unique key is shared."""
    path = tmp_path / "shared.db"
    open_ledger(path).close()
    ledgers = [open_ledger(path) for _ in range(2)]
    gates = [
        ExecutionGate(shared, veto=TwinVeto(armed_twin()), authorize=Authorizer(), clock=Clock())
        for shared in ledgers
    ]
    both_inside = threading.Barrier(2)
    outcomes = {}

    def run(index):
        def action(context):
            both_inside.wait(timeout=10)  # both gates are past Reserve at the same time
            return {}

        outcomes[index] = gates[index].execute(proposal(), action)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    statuses = sorted((o.status, o.reason_code) for o in outcomes.values())
    assert statuses == [(ABORTED, "ALREADY_COMMITTED"), (COMMITTED, None)]
    snapshot = ledgers[0].snapshot()["roots"]
    assert (len(snapshot["AUTHORITY"]), len(snapshot["REJECTION"])) == (1, 1)
    for ledger in ledgers:
        ledger.close()


def test_known_limit_veto_in_the_commit_interval_still_commits(env):
    """C-GATE-001: characterization of an open limit, not a desired behaviour.

    A veto that trips after revalidation but before the ledger append is not seen,
    and the commit goes through. No software check is atomic with a veto source that
    changes independently of the ledger. If this test starts failing because the
    boundary was closed, update it and C-GATE-001 together.
    """
    ledger, twin, _ = env
    real_admit = ledger.admit

    def admit_after_veto(*args, **kwargs):
        twin.run(1, rst_n=1, trigger_in=1, threat_level=0)
        return real_admit(*args, **kwargs)

    ledger.admit = admit_after_veto
    outcome = make_gate(env, Authorizer()).execute(proposal(), staged())
    assert outcome.status == COMMITTED
    assert TwinVeto(twin).vetoed()


def test_known_limit_revocation_in_the_commit_interval_still_commits(env):
    """C-GATE-001: the same limit for a revocation after revalidation, before the append."""
    ledger = env[0]
    authorizer = Authorizer("allow", "allow", "REVOKED")
    real_admit = ledger.admit

    def admit_after_revocation(*args, **kwargs):
        assert authorizer(proposal()).allowed is False  # authority is now revoked
        return real_admit(*args, **kwargs)

    ledger.admit = admit_after_revocation
    outcome = make_gate(env, authorizer).execute(proposal(), staged())
    assert outcome.status == COMMITTED


def test_ledger_failure_while_refusing_raises_and_records_nothing(env):
    """'One receipt per call' holds only while the ledger can record."""
    ledger = env[0]

    def broken(*args, **kwargs):
        raise LedgerBusy("simulated")

    ledger.reject = broken
    action = staged()
    with pytest.raises(LedgerBusy):
        make_gate(env, Authorizer("NO")).execute(proposal(), action)
    assert action.calls == []
    assert roots(env) == (0, 0)


def test_ledger_failure_while_committing_raises_and_releases_the_reservation(env):
    ledger = env[0]
    real_admit = ledger.admit
    gate = make_gate(env, Authorizer())

    def broken(*args, **kwargs):
        raise LedgerBusy("simulated")

    ledger.admit = broken
    with pytest.raises(LedgerBusy):
        gate.execute(proposal(), staged())
    assert roots(env) == (0, 0)
    ledger.admit = real_admit
    assert gate.execute(proposal(), staged()).status == COMMITTED
