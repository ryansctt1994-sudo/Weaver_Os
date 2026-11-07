"""Step 7 acceptance tests A1-A8 (governance/specs/STEP7-EVIDENCE-CUSTODY.md, section 6).

Every witness here is simulated: its key is generated inside the test, by the
same process that writes the ledger. So nothing below is independent
witnessing. The tests show that the checks behave as specified when the key
and the log are held apart from the ledger; who actually holds them is not
something code can test.
"""

from __future__ import annotations

import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from weaver_contracts.canonical import canonicalize
from weaver_contracts.checkpoint import SignedCheckpoint, make_statement, parse_checkpoint
from weaver_contracts.ledger import RootHead
from weaver_verifier.checkpoint import (
    CHECKPOINT_CONSISTENT,
    REFUSED,
    UNWITNESSED,
    custody_report,
)
from weaver_witness.witness import REFUSED as WITNESS_REFUSED
from weaver_witness.witness import SIGNED, UNCHANGED, Witness, WitnessLogError

from tests.ledger.helpers import LEDGER_ID, admit_n, open_ledger


def make_witness(tmp_path, name="witness-a", key=None):
    return Witness(name, key or Ed25519PrivateKey.generate(), tmp_path / f"{name}.log")


def pins(*witnesses):
    return {w.witness_id: w.public_key_hex for w in witnesses}


def reject(ledger, n=1):
    for i in range(n):
        ledger.reject(
            "STATE_TRANSITION",
            {"event": f"denied_{i}", "actor": "L0:Steward"},
            actor_id="op-1",
            policy_version="policy-v1",
            reason_code="POLICY_DENIED",
        )


@pytest.fixture
def honest(tmp_path):
    ledger = open_ledger(tmp_path / "honest.db")
    admit_n(ledger, 3)
    reject(ledger)
    yield ledger
    ledger.close()


@pytest.fixture
def rewritten(tmp_path):
    """The same ledger id, recomputed from scratch with different history."""
    ledger = open_ledger(tmp_path / "rewritten.db")
    admit_n(ledger, 4, start=100)
    reject(ledger)
    yield ledger
    ledger.close()


# --- A1 ------------------------------------------------------------------------


def test_a1_honest_checkpoint_and_extending_snapshot_are_consistent(tmp_path, honest):
    witness = make_witness(tmp_path)
    decision = witness.submit(honest.snapshot())
    assert decision.status == SIGNED

    report = custody_report(honest.snapshot(), [decision.checkpoint], pinned_keys=pins(witness))
    assert report.status == CHECKPOINT_CONSISTENT
    assert report.witnesses == ("witness-a",)
    assert report.corroboration == "UNCORROBORATED"
    assert report.freshness == "COVERED_TO_HEAD"
    # The report never upgrades itself: the witness is simulated, and code cannot tell.
    assert report.independence == "NOT_ESTABLISHED"
    assert report.witness_level == "W0"
    assert "WITNESSED" not in str(report.to_dict())

    admit_n(honest, 2, start=3)
    later = custody_report(honest.snapshot(), [decision.checkpoint], pinned_keys=pins(witness))
    assert later.status == CHECKPOINT_CONSISTENT
    assert later.unwitnessed_entries == {"AUTHORITY": 2, "REJECTION": 0}


# --- A2 ------------------------------------------------------------------------


def test_a2_full_recompute_after_a_signed_checkpoint_is_refused_as_a_fork(
    tmp_path, honest, rewritten
):
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(honest.snapshot()).checkpoint
    # The rewritten store is internally valid and longer, with a fresh anchor of its own.
    assert rewritten.snapshot()["ledger_id"] == LEDGER_ID
    report = custody_report(rewritten.snapshot(), [checkpoint], pinned_keys=pins(witness))
    assert report.status == REFUSED
    assert report.reason.startswith("FORKED: AUTHORITY")
    assert "escalate" in report.reason


# --- A3 ------------------------------------------------------------------------


def test_a3_rewrite_before_any_checkpoint_is_unwitnessed_never_authentic(rewritten):
    report = custody_report(rewritten.snapshot(), [], pinned_keys={})
    assert report.status == UNWITNESSED
    assert report.freshness == "NO_CHECKPOINT"
    assert report.unwitnessed_entries == {"AUTHORITY": 4, "REJECTION": 1}
    assert "AUTHENTIC" not in str(report.to_dict()).upper()


def test_known_limit_a_rewrite_no_witness_ever_saw_is_indistinguishable(tmp_path, rewritten):
    # If the first checkpoint is signed after the rewrite, the witness never saw the honest
    # history, and the rewritten one checks out. This is the stated limitation, not a pass.
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(rewritten.snapshot()).checkpoint
    report = custody_report(rewritten.snapshot(), [checkpoint], pinned_keys=pins(witness))
    assert report.status == CHECKPOINT_CONSISTENT
    assert report.independence == "NOT_ESTABLISHED"


# --- A4 ------------------------------------------------------------------------


def test_a4_witness_refuses_a_forked_state_and_logs_the_refusal(tmp_path, honest, rewritten):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    first = witness.submit(honest.snapshot())
    assert first.status == SIGNED

    refused = witness.submit(rewritten.snapshot())
    assert refused.status == WITNESS_REFUSED
    assert refused.reason.startswith("FORKED")
    assert refused.checkpoint is None
    assert witness.last_checkpoint(LEDGER_ID) == first.checkpoint

    # The refusal is in the witness's own log and survives a restart.
    restarted = make_witness(tmp_path, key=key)
    assert [r["reason"][:6] for r in restarted.refusals()] == ["FORKED"]
    assert restarted.submit(rewritten.snapshot()).status == WITNESS_REFUSED


def test_a4_witness_refuses_a_regressed_state(tmp_path, honest):
    witness = make_witness(tmp_path)
    witness.submit(honest.snapshot())
    truncated = honest.snapshot()
    truncated["roots"]["AUTHORITY"] = truncated["roots"]["AUTHORITY"][:2]
    decision = witness.submit(truncated)
    assert decision.status == WITNESS_REFUSED
    assert decision.reason.startswith("REGRESSED: AUTHORITY")


# --- A5 ------------------------------------------------------------------------


def test_a5_checkpoint_from_an_unpinned_key_is_rejected(tmp_path, honest):
    pinned = make_witness(tmp_path, "witness-a")
    stranger = make_witness(tmp_path, "witness-x")
    checkpoint = stranger.submit(honest.snapshot()).checkpoint
    report = custody_report(honest.snapshot(), [checkpoint], pinned_keys=pins(pinned))
    assert report.status == REFUSED
    assert report.reason.startswith("UNPINNED_KEY")


# --- A6 ------------------------------------------------------------------------


def test_a6_a_checkpoint_cannot_carry_its_own_key(tmp_path, honest):
    # The attacker signs as itself and ships its public key inside the checkpoint.
    attacker = make_witness(tmp_path, "witness-a")
    pinned = make_witness(tmp_path / "real", "witness-a")
    checkpoint = copy.deepcopy(attacker.submit(honest.snapshot()).checkpoint)
    checkpoint["public_key"] = attacker.public_key_hex
    report = custody_report(honest.snapshot(), [checkpoint], pinned_keys=pins(pinned))
    assert report.status == REFUSED and report.reason.startswith("MALFORMED")
    # Without the smuggled key the signature is checked against the pinned key, and fails.
    del checkpoint["public_key"]
    report = custody_report(honest.snapshot(), [checkpoint], pinned_keys=pins(pinned))
    assert report.status == REFUSED and report.reason.startswith("BAD_SIGNATURE")


def test_a6_attacker_signing_as_a_pinned_witness_fails_the_signature(tmp_path, honest):
    pinned = make_witness(tmp_path, "witness-a")
    statement = make_statement(LEDGER_ID, "witness-a", 1, _heads(honest))
    forged = SignedCheckpoint(
        statement, Ed25519PrivateKey.generate().sign(statement.signing_bytes())
    )
    report = custody_report(honest.snapshot(), [forged.to_dict()], pinned_keys=pins(pinned))
    assert report.status == REFUSED and report.reason.startswith("BAD_SIGNATURE")


def test_a6_pinned_keys_must_be_supplied_by_the_caller(honest):
    with pytest.raises(TypeError):
        custody_report(honest.snapshot(), [])  # type: ignore[call-arg]


# --- A7 ------------------------------------------------------------------------


def test_a7_truncation_after_a_signed_checkpoint_is_refused(tmp_path, honest):
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(honest.snapshot()).checkpoint
    truncated = honest.snapshot()
    truncated["roots"]["AUTHORITY"] = truncated["roots"]["AUTHORITY"][:2]
    report = custody_report(truncated, [checkpoint], pinned_keys=pins(witness))
    assert report.status == REFUSED
    assert report.reason.startswith("REGRESSED: AUTHORITY has 2 entries, checkpoint covers 3")


# --- A8 ------------------------------------------------------------------------


def test_a8_absence_is_reported_in_entries_never_as_covered(tmp_path, honest):
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(honest.snapshot()).checkpoint
    admit_n(honest, 5, start=3)
    reject(honest, 2)
    report = custody_report(honest.snapshot(), [checkpoint], pinned_keys=pins(witness))
    assert report.status == CHECKPOINT_CONSISTENT
    assert report.unwitnessed_entries == {"AUTHORITY": 5, "REJECTION": 2}
    assert report.freshness == "NO_CHECKPOINT_FOR_LAST_7_ENTRIES"
    assert report.freshness != "COVERED_TO_HEAD"


# --- Around the acceptance tests ------------------------------------------------


def _heads(ledger):
    return {root: RootHead(h.length, h.head) for root, h in ledger.heads().items()}


def test_two_pinned_witnesses_corroborate(tmp_path, honest):
    a, b = make_witness(tmp_path, "witness-a"), make_witness(tmp_path, "witness-b")
    checkpoints = [a.submit(honest.snapshot()).checkpoint, b.submit(honest.snapshot()).checkpoint]
    report = custody_report(honest.snapshot(), checkpoints, pinned_keys=pins(a, b))
    assert report.status == CHECKPOINT_CONSISTENT
    assert report.witnesses == ("witness-a", "witness-b")
    assert report.corroboration == "CORROBORATED"
    assert report.independence == "NOT_ESTABLISHED"


def test_split_view_between_witnesses_is_refused(tmp_path, honest):
    # Shown two histories at the same length, two witnesses sign different heads.
    rewritten_same_length = open_ledger(tmp_path / "same-length.db")
    admit_n(rewritten_same_length, 3, start=200)
    reject(rewritten_same_length)
    a, b = make_witness(tmp_path, "witness-a"), make_witness(tmp_path, "witness-b")
    checkpoints = [
        a.submit(honest.snapshot()).checkpoint,
        b.submit(rewritten_same_length.snapshot()).checkpoint,
    ]
    report = custody_report(honest.snapshot(), checkpoints, pinned_keys=pins(a, b))
    assert report.status == REFUSED and report.reason.startswith("SPLIT_VIEW")
    rewritten_same_length.close()


def test_a_witness_equivocating_on_one_sequence_number_is_refused(tmp_path, honest):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    first = witness.submit(honest.snapshot()).checkpoint
    admit_n(honest, 1, start=3)
    other = make_statement(LEDGER_ID, "witness-a", 1, _heads(honest))
    second = SignedCheckpoint(other, key.sign(other.signing_bytes())).to_dict()
    report = custody_report(honest.snapshot(), [first, second], pinned_keys=pins(witness))
    assert report.status == REFUSED and report.reason.startswith(
        "SPLIT_VIEW: witness 'witness-a' signed two"
    )


def test_a_witness_regressing_between_its_own_checkpoints_is_refused(tmp_path, honest):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    first = witness.submit(honest.snapshot()).checkpoint
    statement = parse_checkpoint(first).statement
    shorter = make_statement(
        LEDGER_ID,
        "witness-a",
        2,
        {"AUTHORITY": RootHead(0, "0" * 64), "REJECTION": statement.rejection},
    )
    second = SignedCheckpoint(shorter, key.sign(shorter.signing_bytes())).to_dict()
    report = custody_report(honest.snapshot(), [first, second], pinned_keys=pins(witness))
    assert report.status == REFUSED and "regressed AUTHORITY" in report.reason


def test_checkpoint_for_another_ledger_is_refused(tmp_path, honest):
    other = open_ledger(tmp_path / "other.db", ledger_id="wx-other")
    admit_n(other, 3)
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(other.snapshot()).checkpoint
    report = custody_report(honest.snapshot(), [checkpoint], pinned_keys=pins(witness))
    assert report.status == REFUSED
    assert report.reason == "MALFORMED: checkpoint is for ledger 'wx-other'"
    other.close()


def test_invalid_snapshot_is_refused_by_verifier_and_witness(tmp_path, honest):
    broken = honest.snapshot()
    broken["roots"]["AUTHORITY"][1]["event"] = broken["roots"]["AUTHORITY"][1]["event"].replace(
        "1", "9"
    )
    witness = make_witness(tmp_path)
    assert witness.submit(broken).status == WITNESS_REFUSED
    report = custody_report(broken, [], pinned_keys={})
    assert report.status == REFUSED and report.reason.startswith("SNAPSHOT_INVALID")


def test_tampered_statement_is_refused(tmp_path, honest):
    witness = make_witness(tmp_path)
    checkpoint = witness.submit(honest.snapshot()).checkpoint
    bumped = copy.deepcopy(checkpoint)
    bumped["statement"]["checkpoint_seq"] = 7
    report = custody_report(honest.snapshot(), [bumped], pinned_keys=pins(witness))
    assert report.status == REFUSED and report.reason.startswith("BAD_SIGNATURE")
    lengthened = copy.deepcopy(checkpoint)
    lengthened["statement"]["roots"]["AUTHORITY"]["length"] = 2
    report = custody_report(honest.snapshot(), [lengthened], pinned_keys=pins(witness))
    assert report.status == REFUSED and report.reason.startswith("MALFORMED")


def test_signatures_are_domain_separated(tmp_path, honest):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    statement = make_statement(LEDGER_ID, "witness-a", 1, _heads(honest))
    undomained = SignedCheckpoint(statement, key.sign(canonicalize(statement.to_dict())))
    report = custody_report(honest.snapshot(), [undomained.to_dict()], pinned_keys=pins(witness))
    assert report.status == REFUSED and report.reason.startswith("BAD_SIGNATURE")


def test_witness_is_idempotent_and_sequences_extensions(tmp_path, honest):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    first = witness.submit(honest.snapshot())
    again = witness.submit(honest.snapshot())
    assert again.status == UNCHANGED and again.checkpoint == first.checkpoint
    admit_n(honest, 1, start=3)
    second = make_witness(tmp_path, key=key).submit(honest.snapshot())  # after a restart
    assert second.status == SIGNED
    assert second.checkpoint["statement"]["checkpoint_seq"] == 2
    report = custody_report(
        honest.snapshot(), [first.checkpoint, second.checkpoint], pinned_keys=pins(witness)
    )
    assert report.status == CHECKPOINT_CONSISTENT and report.freshness == "COVERED_TO_HEAD"


def test_witness_refuses_to_start_on_a_tampered_log(tmp_path, honest):
    key = Ed25519PrivateKey.generate()
    witness = make_witness(tmp_path, key=key)
    witness.submit(honest.snapshot())
    log = witness.log_path
    log.write_bytes(log.read_bytes().replace(b'"checkpoint_seq":1', b'"checkpoint_seq":2'))
    with pytest.raises(WitnessLogError):
        make_witness(tmp_path, key=key)


def test_witness_refuses_to_start_on_a_log_signed_by_another_key(tmp_path, honest):
    make_witness(tmp_path).submit(honest.snapshot())
    with pytest.raises(WitnessLogError):
        make_witness(tmp_path, key=Ed25519PrivateKey.generate())
