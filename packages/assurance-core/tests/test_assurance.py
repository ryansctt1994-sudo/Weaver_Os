from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weaver_assurance import (
    AuthorityVerifier,
    Chronicle,
    EvidenceLevel,
    EvidenceReceipt,
    KeyGrant,
    SQLiteReplayCache,
    create_envelope,
    evaluate_promotion,
    sign_envelope,
)
from weaver_assurance.authority import public_key_b64
from weaver_assurance.canonical import CanonicalizationError, canonical_json


def test_canonical_profile_rejects_floats():
    try:
        canonical_json({"score": 0.5})
    except CanonicalizationError:
        pass
    else:
        raise AssertionError("float was accepted")


def test_authority_requires_separated_quorum_and_rejects_replay(tmp_path):
    first = Ed25519PrivateKey.generate()
    second = Ed25519PrivateKey.generate()
    grants = [
        KeyGrant("build", public_key_b64(first), "BUILD", 6, 900, 2000),
        KeyGrant("gate", public_key_b64(second), "GATE", 6, 900, 2000),
    ]
    verifier = AuthorityVerifier(grants, SQLiteReplayCache(tmp_path / "replay.db"))
    envelope = create_envelope(
        envelope_id="env-1",
        issuer="agent-planner",
        subject="artifact-1",
        action="execute.test",
        system_id="weaver-test",
        scope_hash="a" * 64,
        nonce="nonce-0001",
        issued_at=1000,
        valid_until=1200,
        requested_authority=4,
        payload={"command": ["python", "-m", "pytest"]},
    )
    one_signature = sign_envelope(envelope, "build", first)
    assert not verifier.verify(one_signature, now=1100).accepted

    complete = sign_envelope(one_signature, "gate", second)
    assert verifier.verify(complete, now=1100).accepted
    replay = verifier.verify(complete, now=1100)
    assert not replay.accepted
    assert replay.reason_codes == ("REPLAY_DETECTED",)


def test_payload_tamper_fails_before_nonce_consumption(tmp_path):
    key = Ed25519PrivateKey.generate()
    verifier = AuthorityVerifier(
        [KeyGrant("gate", public_key_b64(key), "GATE", 3, 900, 2000)],
        SQLiteReplayCache(tmp_path / "replay.db"),
    )
    envelope = create_envelope(
        envelope_id="env-2",
        issuer="planner",
        subject="x",
        action="read",
        system_id="test",
        scope_hash="b" * 64,
        nonce="nonce-0002",
        issued_at=1000,
        valid_until=1200,
        requested_authority=2,
        payload={"x": 1},
    )
    signed = sign_envelope(envelope, "gate", key)
    tampered = signed.__class__(**{**signed.__dict__, "payload": {"x": 2}})
    result = verifier.verify(tampered, now=1100)
    assert not result.accepted
    assert "PAYLOAD_HASH_MISMATCH" in result.reason_codes
    assert not verifier.replay_cache.contains(verifier.replay_key(signed), now=1100)


def test_envelope_cannot_outlive_signing_grant(tmp_path):
    key = Ed25519PrivateKey.generate()
    verifier = AuthorityVerifier(
        [KeyGrant("gate", public_key_b64(key), "GATE", 3, 900, 1150)],
        SQLiteReplayCache(tmp_path / "replay.db"),
    )
    envelope = create_envelope(
        envelope_id="env-grant-window",
        issuer="planner",
        subject="x",
        action="read",
        system_id="test",
        scope_hash="c" * 64,
        nonce="nonce-grant-window",
        issued_at=1000,
        valid_until=1200,
        requested_authority=2,
        payload={"x": 1},
    )
    signed = sign_envelope(envelope, "gate", key)
    assert not verifier.verify(signed, now=1100).accepted
    assert not verifier.replay_cache.contains(verifier.replay_key(signed), now=1100)


def test_sqlite_check_and_record_is_atomic(tmp_path):
    path = tmp_path / "atomic.db"

    def attempt(_: int) -> bool:
        return SQLiteReplayCache(path).check_and_record("same", 2000, now=1000)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(24)))
    assert results.count(True) == 1


def test_chronicle_verifies_and_checkpoint_detects_truncation(tmp_path):
    path = tmp_path / "chronicle.jsonl"
    chronicle = Chronicle(path)
    chronicle.append("START", {"run": "one"}, timestamp_ns=1)
    chronicle.append("END", {"status": "PASS"}, timestamp_ns=2)
    checkpoint = chronicle.checkpoint()
    assert chronicle.verify().valid
    assert chronicle.verify_checkpoint(checkpoint)

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n", encoding="utf-8")
    assert Chronicle(path).verify().valid
    assert not Chronicle(path).verify_checkpoint(checkpoint)


def test_chronicle_refuses_append_after_tamper(tmp_path):
    path = tmp_path / "chronicle.jsonl"
    chronicle = Chronicle(path)
    chronicle.append("EVENT", {"value": 1}, timestamp_ns=1)
    path.write_text(path.read_text().replace('"value":1', '"value":2'), encoding="utf-8")
    try:
        chronicle.append("SECOND", {"value": 3}, timestamp_ns=2)
    except ValueError as exc:
        assert "refusing append" in str(exc)
    else:
        raise AssertionError("append accepted a tampered Chronicle")


def test_receipt_and_cumulative_promotion():
    receipt = EvidenceReceipt.create(
        receipt_id="receipt-1",
        subject="test-suite",
        producer="ci",
        policy_version="v1",
        evidence_level="E2",
        input_hashes={"source": "a" * 64},
        output_hashes={"stdout": "b" * 64},
        command=("pytest", "-q"),
        exit_code=0,
        environment_hash="c" * 64,
        replay_status="LOCAL_PASS",
        created_at="2026-07-14T00:00:00Z",
    )
    assert receipt.verify()
    blocked = evaluate_promotion(EvidenceLevel.E4, {"claim", "scope", "non_claims"})
    assert not blocked.granted
    assert "distinct_witness" in blocked.missing
