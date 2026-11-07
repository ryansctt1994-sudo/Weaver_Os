"""C-GATE-001 candidate: ledger-recorded vetoes and revocations inside the commit transaction.

These tests cover the ledger-authoritative path. They do NOT close C-GATE-001. The
in-memory twin veto is still advisory (see test_gate.py characterization tests), and
closure also needs the veto source to write its state into this ledger.
"""

import threading

import pytest
from weaver_contracts.gate import AuthorizationDecision, Proposal
from weaver_runtime.gate import ABORTED, COMMITTED, ExecutionGate, TwinVeto, revocation_control
from weaver_runtime.ledger import AdmissionError, CommitRefused, LedgerBusy
from weaver_runtime.veto import LuciferLatchTwin

from tests.ledger.helpers import open_ledger


def armed_twin() -> LuciferLatchTwin:
    twin = LuciferLatchTwin()
    twin.run(4, rst_n=0, trigger_in=0, threat_level=0)
    twin.run(4, rst_n=1, trigger_in=0, threat_level=0)
    return twin


def proposal(pid: str = "prop-1") -> Proposal:
    return Proposal(pid, "agent-7", "SET_CONFIG", "policy-v1", {"key": "a", "value": 1})


def authorizer_with_hook(on_revalidate):
    """Allows every call. ``on_revalidate`` runs inside the second (revalidation) call."""
    calls = {"n": 0}

    def authorize(_proposal):
        calls["n"] += 1
        if calls["n"] == 2 and on_revalidate is not None:
            on_revalidate()
        return AuthorizationDecision(True, f"dec-{calls['n']}", valid_until=2000)

    return authorize


def roots(ledger):
    snapshot = ledger.snapshot()["roots"]
    return len(snapshot["AUTHORITY"]), len(snapshot["REJECTION"])


def set_control(ledger, name, value):
    return ledger.set_control(name, value, actor_id="veto-bridge", policy_version="policy-v1")


# --- the revalidation window: a control recorded before the commit ----------------


def test_veto_recorded_in_the_ledger_before_commit_aborts(tmp_path):
    """C-GATE-001 closure criterion, ledger-recorded form.

    A veto is recorded from a second connection while the gate is between revalidation
    and the commit. The commit transaction must see it and refuse. On the pre-candidate
    code this commits, because the gate only looked at its in-memory twin.
    """
    path = tmp_path / "boundary.db"
    gate_ledger = open_ledger(path)
    bridge = open_ledger(path)
    gate = ExecutionGate(
        gate_ledger,
        veto=TwinVeto(armed_twin()),
        authorize=authorizer_with_hook(lambda: set_control(bridge, "veto", "active")),
        clock=lambda: 1000,
    )
    outcome = gate.execute(proposal(), lambda context: {})
    assert (outcome.status, outcome.reason_code) == (ABORTED, "VETO_RECORDED_BEFORE_COMMIT")
    assert roots(gate_ledger) == (0, 1)
    gate_ledger.close()
    bridge.close()


def test_revocation_recorded_in_the_ledger_before_commit_aborts(tmp_path):
    path = tmp_path / "boundary.db"
    gate_ledger = open_ledger(path)
    bridge = open_ledger(path)
    gate = ExecutionGate(
        gate_ledger,
        veto=TwinVeto(armed_twin()),
        authorize=authorizer_with_hook(
            lambda: set_control(bridge, revocation_control("prop-1"), "revoked")
        ),
        clock=lambda: 1000,
    )
    outcome = gate.execute(proposal("prop-1"), lambda context: {})
    assert (outcome.status, outcome.reason_code) == (ABORTED, "REVOKED_RECORDED_BEFORE_COMMIT")
    assert roots(gate_ledger) == (0, 1)
    gate_ledger.close()
    bridge.close()


def test_revocation_of_another_proposal_does_not_block(tmp_path):
    path = tmp_path / "boundary.db"
    gate_ledger = open_ledger(path)
    bridge = open_ledger(path)
    gate = ExecutionGate(
        gate_ledger,
        veto=TwinVeto(armed_twin()),
        authorize=authorizer_with_hook(
            lambda: set_control(bridge, revocation_control("someone-else"), "revoked")
        ),
        clock=lambda: 1000,
    )
    assert gate.execute(proposal("prop-1"), lambda context: {}).status == COMMITTED
    gate_ledger.close()
    bridge.close()


def test_veto_control_with_another_value_does_not_block(tmp_path):
    path = tmp_path / "boundary.db"
    gate_ledger = open_ledger(path)
    bridge = open_ledger(path)
    gate = ExecutionGate(
        gate_ledger,
        veto=TwinVeto(armed_twin()),
        authorize=authorizer_with_hook(lambda: set_control(bridge, "veto", "clear")),
        clock=lambda: 1000,
    )
    assert gate.execute(proposal(), lambda context: {}).status == COMMITTED
    gate_ledger.close()
    bridge.close()


# --- defined semantics: a later control does not undo a commit ---------------------


def test_veto_recorded_after_commit_is_ordered_after_it(tmp_path):
    """Defined semantics: a control written after the commit transaction is simply later.

    The commit stands, and the later veto is recorded as a later fact. Nothing is
    retroactively refused.
    """
    path = tmp_path / "boundary.db"
    ledger = open_ledger(path)
    gate = ExecutionGate(
        ledger,
        veto=TwinVeto(armed_twin()),
        authorize=authorizer_with_hook(None),
        clock=lambda: 1000,
    )
    assert gate.execute(proposal(), lambda context: {}).status == COMMITTED
    set_control(ledger, "veto", "active")
    assert roots(ledger) == (1, 0)
    assert ledger.control("veto") == "active"
    ledger.close()


# --- serialization: a control cannot interleave with a commit ----------------------


def test_control_write_is_serialized_with_an_open_commit(tmp_path):
    path = tmp_path / "boundary.db"
    writer = open_ledger(path)
    other = open_ledger(path, busy_timeout_ms=50)
    inside, release = threading.Event(), threading.Event()

    def guard(_conn):
        inside.set()
        release.wait(timeout=10)

    thread = threading.Thread(
        target=lambda: writer.admit("E", {"n": 1}, actor_id="a", policy_version="p", guard=guard)
    )
    thread.start()
    assert inside.wait(timeout=10)
    with pytest.raises(LedgerBusy):
        set_control(other, "veto", "active")  # the commit transaction holds the store
    release.set()
    thread.join(timeout=10)
    assert set_control(other, "veto", "active") > 0
    writer.close()
    other.close()


# --- ledger-level contract for guards and controls ----------------------------------


def test_refusing_guard_writes_nothing_and_leaves_the_head(tmp_path):
    ledger = open_ledger(tmp_path / "guard.db")
    ledger.admit("E", {"n": 0}, actor_id="a", policy_version="p")

    def refuse(_conn):
        raise CommitRefused("TEST_REFUSAL", "refused inside the transaction")

    with pytest.raises(CommitRefused) as info:
        ledger.admit("E", {"n": 1}, actor_id="a", policy_version="p", guard=refuse)
    assert info.value.reason_code == "TEST_REFUSAL"
    assert roots(ledger) == (1, 0)
    assert ledger.admit("E", {"n": 2}, actor_id="a", policy_version="p").sequence == 1
    ledger.close()


def test_controls_are_logged_and_survive_reopen(tmp_path):
    path = tmp_path / "controls.db"
    ledger = open_ledger(path)
    first = set_control(ledger, "veto", "active")
    second = set_control(ledger, "veto", "clear")
    assert second > first
    assert ledger.control("veto") == "clear"
    ledger.close()
    with open_ledger(path) as reopened:
        assert reopened.control("veto") == "clear"
        assert reopened.control("never-set") is None


@pytest.mark.parametrize("name", ["", "Veto", "1veto", "x" * 200, "has space"])
def test_control_names_are_validated(tmp_path, name):
    ledger = open_ledger(tmp_path / "names.db")
    with pytest.raises(AdmissionError):
        set_control(ledger, name, "active")
    ledger.close()


@pytest.mark.parametrize("value", ["", "x" * 65, 7])
def test_control_values_are_validated(tmp_path, value):
    ledger = open_ledger(tmp_path / "values.db")
    with pytest.raises(AdmissionError):
        set_control(ledger, "veto", value)
    ledger.close()
