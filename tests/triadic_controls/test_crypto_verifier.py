import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import CryptoVerifier, build_signing_object


def b64url_nopad(data: bytes) -> str:
    """Encode bytes as base64url without padding."""

    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def iso_offset(seconds: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=seconds)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")


@pytest.fixture
def keypair():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, b64url_nopad(public_key_bytes)


@pytest.fixture
def mock_registry(keypair):
    _, public_key_b64url = keypair
    return {
        "issuers": [
            {
                "issuer_id": "11111111-1111-4111-8111-111111111111",
                "key_id": "22222222-2222-4222-8222-222222222222",
                "public_key": public_key_b64url,
                "status": "ACTIVE",
                "assigned_roles": ["role-level-4-grant"],
            }
        ],
        "roles": [
            {
                "role_id": "role-level-4-grant",
                "separation_group": "group-alpha",
                "may_grant_authority": True,
                "may_revoke_or_refuse": False,
                "max_grant_level": 4,
                "can_participate_in_quorum": True,
            }
        ],
    }


def signed_envelope(
    private_key,
    *,
    nonce: str,
    payload_hash: str = "a" * 64,
    scope_hash: str = "b" * 64,
    valid_from: str | None = None,
    valid_until: str | None = None,
):
    issuer_id = "11111111-1111-4111-8111-111111111111"
    key_id = "22222222-2222-4222-8222-222222222222"
    envelope = {
        "payload_type": "AUTHORITY_TOKEN",
        "payload_schema_version": "0.4.0",
        "payload_hash_alg": "sha256",
        "payload_hash": payload_hash,
        "signing_domain": "triadic-controls:v0.4.0:authority-token",
        "replay_domain": {
            "system_id": "rover-7",
            "scope_hash": scope_hash,
            "valid_from": valid_from or iso_offset(-60),
            "valid_until": valid_until or iso_offset(3600),
        },
        "signatures": [],
    }
    signing_message = build_signing_object(
        signing_domain=envelope["signing_domain"],
        payload_type=envelope["payload_type"],
        payload_schema_version=envelope["payload_schema_version"],
        payload_hash=envelope["payload_hash"],
        replay_domain=envelope["replay_domain"],
        nonce_or_sequence=nonce,
    )
    signature_bytes = private_key.sign(signing_message)
    envelope["signatures"].append(
        {
            "issuer_id": issuer_id,
            "key_id": key_id,
            "algorithm": "ed25519",
            "signature_encoding": "base64url",
            "signature": b64url_nopad(signature_bytes),
            "nonce_or_sequence": nonce,
            "signed_at": iso_offset(0),
        }
    )
    return envelope


def test_valid_envelope_then_replay_detected(keypair, mock_registry):
    private_key, _ = keypair
    cache = InMemoryReplayCache()
    verifier = CryptoVerifier(key_registry=mock_registry, replay_cache=cache)

    envelope = signed_envelope(private_key, nonce="seq-0001")

    result_1 = verifier.verify_authority_token(envelope, requested_level=4)
    assert result_1.is_valid is False
    assert "INSUFFICIENT_QUORUM" in result_1.failure_codes

    # Level 4 requires two independent separation groups. Reusing the same
    # one-signature envelope should still be rejected, preserving quorum safety.
    result_2 = verifier.verify_authority_token(envelope, requested_level=4)
    assert result_2.is_valid is False
    assert "REPLAY_DETECTED" in result_2.failure_codes


def test_valid_level_3_envelope_then_replay_detected(keypair, mock_registry):
    private_key, _ = keypair
    cache = InMemoryReplayCache()
    verifier = CryptoVerifier(key_registry=mock_registry, replay_cache=cache)

    envelope = signed_envelope(
        private_key,
        nonce="seq-0002",
        payload_hash="c" * 64,
        scope_hash="d" * 64,
    )

    result_1 = verifier.verify_authority_token(envelope, requested_level=3)
    assert result_1.is_valid is True
    assert result_1.ledger_event_type == "TOKEN_SIGNATURE_VALIDATED"
    assert result_1.effective_max_authority_level == 3

    result_2 = verifier.verify_authority_token(envelope, requested_level=3)
    assert result_2.is_valid is False
    assert "REPLAY_DETECTED" in result_2.failure_codes


def test_expired_replay_domain_rejected_before_signature_acceptance(keypair, mock_registry):
    private_key, _ = keypair
    verifier = CryptoVerifier(key_registry=mock_registry, replay_cache=InMemoryReplayCache())
    envelope = signed_envelope(
        private_key,
        nonce="seq-expired",
        valid_from=iso_offset(-7200),
        valid_until=iso_offset(-3600),
    )

    result = verifier.verify_authority_token(envelope, requested_level=3)
    assert result.is_valid is False
    assert result.ledger_event_type == "TIME_ATTESTATION_FAILED"
    assert result.failure_codes == ["TIME_WINDOW_INVALID"]


def test_future_replay_domain_rejected_before_signature_acceptance(keypair, mock_registry):
    private_key, _ = keypair
    verifier = CryptoVerifier(key_registry=mock_registry, replay_cache=InMemoryReplayCache())
    envelope = signed_envelope(
        private_key,
        nonce="seq-future",
        valid_from=iso_offset(3600),
        valid_until=iso_offset(7200),
    )

    result = verifier.verify_authority_token(envelope, requested_level=3)
    assert result.is_valid is False
    assert result.ledger_event_type == "TIME_ATTESTATION_FAILED"
    assert result.failure_codes == ["TIME_WINDOW_INVALID"]
