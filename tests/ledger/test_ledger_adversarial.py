"""Adversarial verification of ledger snapshots.

T1-T12 port the cathedral-verified Chronicle suite (chronicle/test_chronicle.py) to
the ReceiptLedger and its read-only verifier. X-tests are new cases that only arise
with a Dual Ledger, receipts, and canonical bytes.
"""

import copy
import hashlib
import json
import sqlite3

import pytest
from weaver_contracts.canonical import canonicalize
from weaver_contracts.receipt import build
from weaver_verifier.ledger import verify_snapshot

from tests.ledger.helpers import admit_n, open_ledger


def fresh(tmp_path, n=5, name="ledger.db", values=None):
    with open_ledger(tmp_path / name) as ledger:
        if values is None:
            admit_n(ledger, n)
        else:
            for i, value in enumerate(values):
                ledger.admit(
                    "STATE_TRANSITION",
                    {"event": f"e{i}", "value": value},
                    actor_id="op-1",
                    policy_version="policy-v1",
                )
        return ledger.snapshot(), ledger.anchor().to_dict()


def authority(snapshot):
    return snapshot["roots"]["AUTHORITY"]


def reseal(entry, **receipt_changes):
    """Recompute one entry's digests the way an attacker with write access would."""
    receipt = dict(entry["receipt"])
    receipt.update(receipt_changes)
    receipt["event_digest"] = hashlib.sha256(entry["event"].encode()).hexdigest()
    derived = {"schema", "canonicalization", "receipt_digest"}
    body = {k: v for k, v in receipt.items() if k not in derived}
    entry["receipt"] = build(**body).to_dict()


def set_value(entry, value):
    event = json.loads(entry["event"])
    event["value"] = value
    entry["event"] = canonicalize(event).decode()


# --- Cathedral T1-T12 -------------------------------------------------------


def test_T1_honest_chain_verifies(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    assert verify_snapshot(snapshot).ok
    assert verify_snapshot(snapshot, anchor=anchor).ok


def test_T2_payload_edit_detected(tmp_path):
    snapshot, _ = fresh(tmp_path)
    set_value(authority(snapshot)[2], 999)
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok
    assert "AUTHORITY[2]" in verdict.reason and "event digest" in verdict.reason


def test_T3_local_reseal_breaks_downstream_link(tmp_path):
    snapshot, _ = fresh(tmp_path)
    set_value(authority(snapshot)[2], 999)
    reseal(authority(snapshot)[2])
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok
    assert "AUTHORITY[3]" in verdict.reason and "broken link" in verdict.reason


def test_T4_reorder_detected(tmp_path):
    snapshot, _ = fresh(tmp_path)
    entries = authority(snapshot)
    entries[1], entries[3] = entries[3], entries[1]
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "sequence mismatch" in verdict.reason


def test_T5_deletion_detected(tmp_path):
    snapshot, _ = fresh(tmp_path)
    del authority(snapshot)[2]
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "AUTHORITY[2]" in verdict.reason


def test_T6_truncation_is_internally_valid_without_anchor(tmp_path):
    snapshot, _ = fresh(tmp_path)
    full = verify_snapshot(snapshot).chronicle_root
    del authority(snapshot)[3:]
    verdict = verify_snapshot(snapshot)
    assert verdict.ok and not verdict.anchored
    assert "not detectable without an anchor" in verdict.reason
    assert verdict.chronicle_root != full


def test_T7_forged_insert_detected(tmp_path):
    snapshot, _ = fresh(tmp_path)
    forged = copy.deepcopy(authority(snapshot)[2])
    forged["event"] = canonicalize({"event": "FORGED", "actor": "attacker", "value": -1}).decode()
    authority(snapshot).insert(2, forged)
    assert not verify_snapshot(snapshot).ok


def test_T9_on_disk_tamper_detected(tmp_path):
    path = tmp_path / "ledger.db"
    with open_ledger(path) as ledger:
        admit_n(ledger, 5)
    con = sqlite3.connect(path)
    con.execute(
        "UPDATE entries SET event = ? WHERE root = 'AUTHORITY' AND sequence = 2",
        (canonicalize({"event": "action_2", "actor": "L0:Steward", "value": 7777}),),
    )
    con.commit()
    con.close()
    with open_ledger(path) as ledger:
        verdict = verify_snapshot(ledger.snapshot())
    assert not verdict.ok and "AUTHORITY[2]" in verdict.reason


def test_T10_chronicle_root_is_deterministic_and_content_sensitive(tmp_path):
    a, _ = fresh(tmp_path, name="a.db", values=[0, 1, 2, 3, 4])
    b, _ = fresh(tmp_path, name="b.db", values=[0, 1, 2, 3, 4])
    c, _ = fresh(tmp_path, name="c.db", values=[0, 1, 2, 3, 99])
    root_a = verify_snapshot(a).chronicle_root
    assert root_a == verify_snapshot(b).chronicle_root
    assert root_a != verify_snapshot(c).chronicle_root


def test_T11_anchor_detects_truncation(tmp_path):
    snapshot, anchor = fresh(tmp_path, values=[0, 1, 2, 3, 4, 5, 6])
    assert verify_snapshot(snapshot, anchor=anchor).ok
    del authority(snapshot)[4:]
    verdict = verify_snapshot(snapshot, anchor=anchor)
    assert not verdict.ok and "truncation" in verdict.reason


def test_T12_full_forward_rewrite_fails_anchor(tmp_path):
    rewritten, _ = fresh(tmp_path, name="fake.db", values=[9, 9, 9])
    _, real_anchor = fresh(tmp_path, name="real.db", values=[0, 1, 2])
    assert verify_snapshot(rewritten).ok
    verdict = verify_snapshot(rewritten, anchor=real_anchor)
    assert not verdict.ok and "rewrite" in verdict.reason


# --- new cases --------------------------------------------------------------


def test_X1_last_entry_reseal_is_caught_only_by_anchor(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    set_value(authority(snapshot)[4], 999)
    reseal(authority(snapshot)[4])
    assert verify_snapshot(snapshot).ok
    verdict = verify_snapshot(snapshot, anchor=anchor)
    assert not verdict.ok and "rewrite" in verdict.reason


def test_X2_non_canonical_event_bytes_rejected_even_with_matching_digest(tmp_path):
    snapshot, _ = fresh(tmp_path)
    entry = authority(snapshot)[4]
    entry["event"] = json.dumps(json.loads(entry["event"]), indent=1)
    reseal(entry)
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "not WX-CJSON-1 canonical" in verdict.reason


def test_X3_rejection_cannot_be_moved_onto_authority_root(tmp_path):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        ledger.reject(
            "PROMOTION", {"to": "R4"}, actor_id="op", policy_version="p", reason_code="NO"
        )
        snapshot = ledger.snapshot()
    snapshot["roots"]["AUTHORITY"].append(snapshot["roots"]["REJECTION"].pop())
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "root REJECTION" in verdict.reason


def test_X4_relabelled_rejection_is_not_admissible_state(tmp_path):
    with open_ledger(tmp_path / "ledger.db") as ledger:
        ledger.reject(
            "PROMOTION", {"to": "R4"}, actor_id="op", policy_version="p", reason_code="NO"
        )
        snapshot = ledger.snapshot()
    moved = snapshot["roots"]["REJECTION"].pop()
    moved["receipt"]["root"] = "AUTHORITY"
    snapshot["roots"]["AUTHORITY"].append(moved)
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "receipt invalid" in verdict.reason


def test_X5_receipt_from_another_ledger_rejected(tmp_path):
    snapshot, _ = fresh(tmp_path)
    snapshot["ledger_id"] = "wx-other"
    verdict = verify_snapshot(snapshot)
    assert not verdict.ok and "belongs to ledger" in verdict.reason


def test_X6_anchor_for_another_ledger_rejected(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    anchor = dict(anchor, ledger_id="wx-other")
    verdict = verify_snapshot(snapshot, anchor=anchor)
    assert not verdict.ok and "anchor invalid" in verdict.reason


def test_X7_tampered_anchor_rejected(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    anchor["chronicle_root"] = "00" * 32
    verdict = verify_snapshot(snapshot, anchor=anchor)
    assert not verdict.ok and "anchor invalid" in verdict.reason


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(extra=1),
        lambda s: s.update(schema="wx-ledger-snapshot-0"),
        lambda s: s["roots"].update(SHADOW=[]),
        lambda s: s["roots"]["AUTHORITY"][0].update(note="x"),
        lambda s: s["roots"]["AUTHORITY"][0].update(event=b"{}"),
    ],
    ids=["extra-field", "schema", "extra-root", "extra-entry-field", "bytes-event"],
)
def test_X8_shape_is_strict(tmp_path, mutate):
    snapshot, _ = fresh(tmp_path)
    mutate(snapshot)
    assert not verify_snapshot(snapshot).ok


def test_X9_verifier_does_not_modify_its_input(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    before = copy.deepcopy((snapshot, anchor))
    verify_snapshot(snapshot, anchor=anchor)
    set_value(authority(snapshot)[1], 5)
    tampered = copy.deepcopy(snapshot)
    verify_snapshot(snapshot, anchor=anchor)
    assert snapshot == tampered
    assert before[1] == anchor


def test_X10_snapshot_is_itself_canonicalizable(tmp_path):
    snapshot, anchor = fresh(tmp_path)
    exported = canonicalize(snapshot)
    assert verify_snapshot(json.loads(exported), anchor=json.loads(canonicalize(anchor))).ok
