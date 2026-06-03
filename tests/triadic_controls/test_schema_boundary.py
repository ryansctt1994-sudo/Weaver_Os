import pytest

from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import CryptoVerifier


@pytest.fixture
def minimal_schemas():
    """Minimal local schemas for testing the verifier schema boundary."""

    return {
        "key_registry": {
            "type": "object",
            "properties": {
                "registry_version": {"type": "string"}
            },
            "required": ["registry_version"],
        },
        "signature_envelope": {
            "type": "object",
            "properties": {
                "payload_type": {"type": "string"},
                "nonce_or_sequence": {"type": "string"},
            },
            "required": ["payload_type", "nonce_or_sequence"],
        },
    }


@pytest.fixture
def valid_minimal_registry():
    return {
        "registry_version": "0.4.1",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2027-01-01T00:00:00Z",
        "issuers": [],
        "roles": [],
    }


def test_verifier_halts_on_invalid_registry_schema(minimal_schemas):
    bad_registry = {"registry_version": 404}

    with pytest.raises(ValueError, match="Key registry failed schema validation"):
        CryptoVerifier(
            key_registry=bad_registry,
            replay_cache=InMemoryReplayCache(),
            schemas=minimal_schemas,
        )


def test_verifier_rejects_invalid_envelope_schema(valid_minimal_registry, minimal_schemas):
    verifier = CryptoVerifier(
        key_registry=valid_minimal_registry,
        replay_cache=InMemoryReplayCache(),
        schemas=minimal_schemas,
    )
    bad_envelope = {"payload_type": 12345}

    result = verifier.verify_authority_token(bad_envelope, requested_level=3)

    assert result.is_valid is False
    assert result.ledger_event_type == "SIGNATURE_VERIFICATION_FAILED"
    assert "MALFORMED_ENVELOPE" in result.failure_codes
