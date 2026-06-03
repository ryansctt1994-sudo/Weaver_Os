import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import CryptoVerifier, build_signing_object


def b64url_nopad(data: bytes) -> str:
    """Encode bytes as base64url without padding."""

    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


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


def test_valid_envelope_then_replay_detected(keypair, mock_registry):
    private_key, _ = keypair
    cache = InMemoryReplayCache()
    verifier = CryptoVerifier(key_registry=mock_registry, replay_cache=cache)

    issuer_id = "11111111-1111-4111-8111-111111111111"
    key_id = "22222222-2222-4222-8222-222222222222"
    nonce = "seq-0001"

    envelope = {
        "payload_type": "AUTHORITY_TOKEN",
        "payload_schema_version": "0.4.0",
        "payload_hash_alg": "sha256",
        "payload_hash": "a" * 64,
        "signing_domain": "triadic-controls:v0.4.0:authority-token",
        "replay_domain": {
            "system_id": "rover-7",
            "scope_hash": "b" * 64,
            "valid_from": "2026-06-02T10:00:00Z",
            "valid_until": "2026-06-02T11:00:00Z",
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
            "signed_at": "2026-06-02T10:05:00Z",
        }
    )

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

    issuer_id = "11111111-1111-4111-8111-111111111111"
    key_id = "22222222-2222-4222-8222-222222222222"
    nonce = "seq-0002"

    envelope = {
        "payload_type": "AUTHORITY_TOKEN",
        "payload_schema_version": "0.4.0",
        "payload_hash_alg": "sha256",
        "payload_hash": "c" * 64,
        "signing_domain": "triadic-controls:v0.4.0:authority-token",
        "replay_domain": {
            "system_id": "rover-7",
            "scope_hash": "d" * 64,
            "valid_from": "2026-06-02T10:00:00Z",
            "valid_until": "2026-06-02T11:00:00Z",
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
            "signed_at": "2026-06-02T10:05:00Z",
        }
    )

    result_1 = verifier.verify_authority_token(envelope, requested_level=3)
    assert result_1.is_valid is True
    assert result_1.ledger_event_type == "TOKEN_SIGNATURE_VALIDATED"
    assert result_1.effective_max_authority_level == 3

    result_2 = verifier.verify_authority_token(envelope, requested_level=3)
    assert result_2.is_valid is False
    assert "REPLAY_DETECTED" in result_2.failure_codes
