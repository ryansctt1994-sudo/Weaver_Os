"""ADR-0006 runtime rules for the single-owner ReceiptLedger."""

import copy
import hashlib
import json
import sqlite3

import pytest
from weaver_contracts.canonical import canonicalize
from weaver_contracts.receipt import GENESIS_DIGEST, Receipt
from weaver_runtime.ledger import AdmissionError, LedgerCorrupted, LedgerDuplicate, LedgerError
from weaver_verifier.ledger import verify_snapshot

from tests.ledger.helpers import admit_n, open_ledger


@pytest.fixture()
def ledger(tmp_path):
    with open_ledger(tmp_path / "ledger.db") as instance:
        yield instance


# --- positive append and replay -------------------------------------------


def test_append_assigns_sequence_and_links(ledger):
    receipts = admit_n(ledger, 3)
    assert [r.sequence for r in receipts] == [0, 1, 2]
    assert receipts[0].predecessor_digest == GENESIS_DIGEST
    assert receipts[1].predecessor_digest == receipts[0].receipt_digest
    assert receipts[2].predecessor_digest == receipts[1].receipt_digest
    assert verify_snapshot(ledger.snapshot()).ok


def test_roots_have_independent_chains(ledger):
    admit_n(ledger, 2)
    first = ledger.reject(
        "PROMOTION", {"to": "R4"}, actor_id="op-2", policy_version="p1", reason_code="NO_WITNESS"
    )
    second = ledger.reject(
        "FORK",
        {"head": "x"},
        actor_id="op-2",
        policy_version="p1",
        reason_code="FORK_DETECTED",
        quarantine=True,
    )
    assert (first.root, first.sequence) == ("REJECTION", 0)
    assert first.predecessor_digest == GENESIS_DIGEST
    assert second.admissibility == "QUARANTINED"
    heads = ledger.heads()
    assert heads["AUTHORITY"].length == 2
    assert heads["REJECTION"].length == 2
    assert verify_snapshot(ledger.snapshot(), anchor=ledger.anchor().to_dict()).ok


def test_lumen_shape_event_type_data_metadata(ledger):
    """Lumen's Chronicle entry shape (event_type, data, metadata) maps onto event content."""
    receipt = ledger.admit(
        "START",
        {"data": {"ok": True}, "metadata": {"source": "freelattice"}},
        actor_id="op-1",
        policy_version="p1",
    )
    assert receipt.event_type == "START"
    stored = ledger.snapshot()["roots"]["AUTHORITY"][0]["event"]
    assert stored == '{"data":{"ok":true},"metadata":{"source":"freelattice"}}'


def test_replay_reconstructs_identical_chain(tmp_path):
    """Same canonical event sequence and clock -> same receipts, same Chronicle Root."""
    with open_ledger(tmp_path / "a.db") as original:
        admit_n(original, 4)
        original.reject(
            "POLICY", {"x": 1}, actor_id="op-9", policy_version="p1", reason_code="DENIED"
        )
        snapshot = original.snapshot()
        anchor = original.anchor()
    with open_ledger(tmp_path / "b.db") as replica:
        for entry in snapshot["roots"]["AUTHORITY"]:
            r = entry["receipt"]
            replica.admit(
                r["event_type"],
                json.loads(entry["event"]),
                actor_id=r["actor_id"],
                policy_version=r["policy_version"],
            )
        for entry in snapshot["roots"]["REJECTION"]:
            r = entry["receipt"]
            replica.reject(
                r["event_type"],
                json.loads(entry["event"]),
                actor_id=r["actor_id"],
                policy_version=r["policy_version"],
                reason_code=r["reason_code"],
            )
        assert replica.snapshot() == snapshot
        assert replica.anchor() == anchor


def test_persistence_round_trip(tmp_path):
    """Cathedral T8: write, close, reopen; the chain verifies and the head matches."""
    path = tmp_path / "ledger.db"
    with open_ledger(path) as first:
        admit_n(first, 10)
        anchor = first.anchor().to_dict()
    with open_ledger(path) as reopened:
        assert reopened.anchor().to_dict() == anchor
        assert verify_snapshot(reopened.snapshot(), anchor=anchor).ok
        assert admit_n(reopened, 1, start=10)[0].sequence == 10


# --- callers cannot own linkage state --------------------------------------


@pytest.mark.parametrize(
    "kwarg", ["sequence", "predecessor_digest", "receipt_digest", "root", "committed_at"]
)
def test_callers_cannot_supply_linkage(ledger, kwarg):
    with pytest.raises(TypeError):
        ledger.admit("E", {"a": 1}, actor_id="op-1", policy_version="p1", **{kwarg: "x"})


def test_store_belongs_to_one_ledger(tmp_path):
    path = tmp_path / "ledger.db"
    open_ledger(path).close()
    with pytest.raises(LedgerError, match="belongs to ledger"):
        open_ledger(path, ledger_id="other-ledger")


# --- failed appends do not advance -----------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda led: led.admit("E", {"price": 1.5}, actor_id="op-1", policy_version="p1"),
        lambda led: led.admit("E", {"n": 2**60}, actor_id="op-1", policy_version="p1"),
        lambda led: led.admit("E", ["not", "an", "object"], actor_id="op-1", policy_version="p1"),
        lambda led: led.admit("lowercase", {"a": 1}, actor_id="op-1", policy_version="p1"),
        lambda led: led.admit("E", {"a": 1}, actor_id="TBD", policy_version="p1"),
        lambda led: led.reject(
            "E", {"a": 1}, actor_id="op-1", policy_version="p1", reason_code="bad"
        ),
    ],
    ids=["float", "unsafe-int", "non-object", "bad-event-type", "placeholder-actor", "bad-reason"],
)
def test_failed_admission_does_not_advance(ledger, call):
    admit_n(ledger, 2)
    before = ledger.anchor()
    with pytest.raises(AdmissionError):
        call(ledger)
    assert ledger.anchor() == before
    assert admit_n(ledger, 1, start=2)[0].sequence == 2


def test_failure_inside_transaction_rolls_back(ledger, monkeypatch):
    """Interrupted transaction: the entry insert happened, the head update fails."""
    admit_n(ledger, 2)
    before = ledger.snapshot()

    def boom(receipt):
        raise RuntimeError("simulated failure after insert")

    monkeypatch.setattr(ledger, "_advance_head", boom)
    with pytest.raises(RuntimeError, match="simulated"):
        admit_n(ledger, 1, start=2)
    monkeypatch.undo()
    assert ledger.snapshot() == before
    assert admit_n(ledger, 1, start=2)[0].sequence == 2
    assert verify_snapshot(ledger.snapshot()).ok


# --- mutation isolation: ingress, storage, return --------------------------


def test_ingress_mutation_after_append_changes_nothing(ledger):
    event = {"nested": {"value": 1}, "items": [1, 2]}
    receipt = ledger.admit("E", event, actor_id="op-1", policy_version="p1")
    event["nested"]["value"] = 999
    event["items"].append(3)
    stored = ledger.snapshot()["roots"]["AUTHORITY"][0]
    assert stored["event"] == '{"items":[1,2],"nested":{"value":1}}'
    assert verify_snapshot(ledger.snapshot()).ok
    assert receipt.event_digest == hashlib.sha256(stored["event"].encode()).hexdigest()


def test_stored_bytes_are_the_hashed_bytes(ledger, tmp_path):
    receipt = ledger.admit("E", {"b": 2, "a": 1}, actor_id="op-1", policy_version="p1")
    con = sqlite3.connect(tmp_path / "ledger.db")
    event, stored_receipt = con.execute("SELECT event, receipt FROM entries").fetchone()
    con.close()
    assert event == canonicalize({"a": 1, "b": 2})
    assert hashlib.sha256(event).hexdigest() == receipt.event_digest
    assert stored_receipt == receipt.to_canonical()


def test_returned_objects_do_not_alias_store(ledger):
    receipt = admit_n(ledger, 2)[0]
    assert isinstance(receipt, Receipt)
    with pytest.raises(AttributeError):
        receipt.sequence = 7  # type: ignore[misc]
    snapshot = ledger.snapshot()
    pristine = copy.deepcopy(snapshot)
    snapshot["roots"]["AUTHORITY"][0]["receipt"]["sequence"] = 99
    snapshot["roots"]["AUTHORITY"].clear()
    assert ledger.snapshot() == pristine


# --- the ledger refuses to extend a corrupted store ------------------------


def _tamper(path, sql, params=()):
    con = sqlite3.connect(path)
    con.execute(sql, params)
    con.commit()
    con.close()


def test_refuses_to_extend_when_head_row_is_rewound(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path) as ledger:
        admit_n(ledger, 3)
    _tamper(path, "UPDATE heads SET length = 2 WHERE root = 'AUTHORITY'")
    with open_ledger(path) as ledger, pytest.raises(LedgerCorrupted):
        admit_n(ledger, 1, start=3)


def test_refuses_to_extend_when_last_entry_is_deleted(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path) as ledger:
        admit_n(ledger, 3)
    _tamper(path, "DELETE FROM entries WHERE root = 'AUTHORITY' AND sequence = 2")
    with open_ledger(path) as ledger, pytest.raises(LedgerCorrupted):
        admit_n(ledger, 1, start=3)


def test_refuses_to_extend_when_head_digest_is_swapped(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path) as ledger:
        admit_n(ledger, 3)
    _tamper(path, "UPDATE heads SET head = ? WHERE root = 'AUTHORITY'", ("ab" * 32,))
    with open_ledger(path) as ledger, pytest.raises(LedgerCorrupted):
        admit_n(ledger, 1, start=3)


# --- unique keys ------------------------------------------------------------------


def test_unique_key_is_enforced_across_instances(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path) as first, open_ledger(path) as second:
        first.admit("E", {"n": 1}, actor_id="op-1", policy_version="p1", unique_key="k-1")
        before = second.anchor()
        with pytest.raises(LedgerDuplicate):
            second.admit("E", {"n": 2}, actor_id="op-1", policy_version="p1", unique_key="k-1")
        assert second.anchor() == before
        second.admit("E", {"n": 3}, actor_id="op-1", policy_version="p1", unique_key="k-2")


def test_failed_append_does_not_consume_its_unique_key(ledger):
    with pytest.raises(AdmissionError):
        ledger.admit("E", {"x": 1.5}, actor_id="op-1", policy_version="p1", unique_key="k")
    assert ledger.admit("E", {"x": 1}, actor_id="op-1", policy_version="p1", unique_key="k")


@pytest.mark.parametrize("key", ["", 7])
def test_unique_key_must_be_a_non_empty_string(ledger, key):
    with pytest.raises(AdmissionError):
        ledger.admit("E", {"x": 1}, actor_id="op-1", policy_version="p1", unique_key=key)
