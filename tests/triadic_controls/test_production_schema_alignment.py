import base64
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import (
    CryptoVerifier,
    build_signing_object,
    canonicalize_json,
    compute_payload_hash,
)


def b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def iso_offset(seconds: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=seconds)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")


def sign_registry(registry: dict, root_signing_key) -> dict:
    signed_registry = copy.deepcopy(registry)
    signature = root_signing_key.sign(canonicalize_json(signed_registry))
    signed_registry["registry_signature"] = b64url_nopad(signature)
    return signed_registry


def schema_bundle(production_schemas):
    return {
        "key_registry": production_schemas["key_registry"],
        "issuer_record": production_schemas["issuer_record"],
        "role_policy": production_schemas["role_policy"],
        "signature_envelope": production_schemas["signature_envelope"],
    }


@pytest.fixture(scope="session")
def production_schemas():
    base_path = Path(__file__).parent.parent.parent / "triadic_controls" / "schemas"
    schemas = {}
    for schema_name in [
        "issuer_record",
        "role_policy",
        "key_registry",
        "signature_envelope",
        "verification_result",
    ]:
        with open(base_path / f"{schema_name}.schema.json", "r", encoding="utf-8") as handle:
            schemas[schema_name] = json.load(handle)
    return schemas


@pytest.fixture
def root_keypair():
    signing_key = ed25519.Ed25519PrivateKey.generate()
    public_key = signing_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return signing_key, b64url_nopad(public_key_bytes)


@pytest.fixture
def issuer_keypair():
    signing_key = ed25519.Ed25519PrivateKey.generate()
    public_key = signing_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return signing_key, b64url_nopad(public_key_bytes)


@pytest.fixture
def production_registry(issuer_keypair, root_keypair):
    _, issuer_public_key_b64url = issuer_keypair
    root_signing_key, _ = root_keypair
    unsigned = {
        "registry_id": "00000000-0000-4000-8000-000000000000",
        "registry_version": "0.5.0",
        "registry_sequence": 1,
        "valid_from": iso_offset(-3600),
        "valid_until": iso_offset(3600),
        "last_updated": iso_offset(-60),
        "issuers": [
            {
                "issuer_id": "11111111-1111-4111-8111-111111111111",
                "key_id": "22222222-2222-4222-8222-222222222222",
                "public_key_encoding": "base64url",
                "public_key": issuer_public_key_b64url,
                "key_type": "ed25519",
                "status": "ACTIVE",
                "issued_at": iso_offset(-3600),
                "expires_at": iso_offset(3600),
                "assigned_roles": ["role-level-4-grant"],
            }
        ],
        "roles": [
            {
                "role_id": "role-level-4-grant",
                "description": "Test role for Level 4 grant participation.",
                "separation_group": "group-alpha",
                "max_grant_level": 4,
                "may_grant_authority": True,
                "may_revoke_or_refuse": False,
                "can_participate_in_quorum": True,
                "allowed_scopes": {
                    "systems": ["rover-7"],
                    "regions": ["sector_7"],
                    "tasks": ["navigation"],
                    "max_authority_duration_sec": 3600,
                },
            }
        ],
    }
    return sign_registry(unsigned, root_signing_key)


def authority_payload(level: int = 3) -> dict:
    return {
        "token_id": "33333333-3333-4333-8333-333333333333",
        "system_id": "rover-7",
        "authority_level": level,
        "scope": {"task": "navigation", "region": "sector_7"},
    }


def signed_production_envelope(signing_key, inner_payload: dict, nonce: str = "seq-prod-0001") -> dict:
    payload_hash = compute_payload_hash(inner_payload)
    replay_domain = {
        "system_id": "rover-7",
        "scope_hash": "b" * 64,
        "valid_from": iso_offset(-60),
        "valid_until": iso_offset(3600),
    }
    envelope = {
        "payload_type": "AUTHORITY_TOKEN",
        "payload_schema_version": "0.5.0",
        "payload_hash_alg": "sha256",
        "payload_hash": payload_hash,
        "signing_domain": "triadic-controls:v0.5.0:authority-token",
        "replay_domain": replay_domain,
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
    signature = signing_key.sign(signing_message)
    envelope["signatures"].append(
        {
            "issuer_id": "11111111-1111-4111-8111-111111111111",
            "key_id": "22222222-2222-4222-8222-222222222222",
            "algorithm": "ed25519",
            "signature_encoding": "base64url",
            "signature": b64url_nopad(signature),
            "nonce_or_sequence": nonce,
            "signed_at": iso_offset(0),
        }
    )
    return envelope


def make_verifier(production_registry, production_schemas, root_keypair):
    _, root_public_key_b64url = root_keypair
    return CryptoVerifier(
        key_registry=production_registry,
        replay_cache=InMemoryReplayCache(),
        schemas=schema_bundle(production_schemas),
        root_public_key_b64url=root_public_key_b64url,
    )


def test_production_schemas_accept_valid_registry_and_envelope(
    issuer_keypair,
    root_keypair,
    production_registry,
    production_schemas,
):
    signing_key, _ = issuer_keypair
    payload = authority_payload(level=3)
    envelope = signed_production_envelope(signing_key, payload)
    verifier = make_verifier(production_registry, production_schemas, root_keypair)

    result = verifier.verify_authority_token(envelope, requested_level=3, inner_payload=payload)

    assert result.is_valid is True
    assert result.ledger_event_type == "TOKEN_SIGNATURE_VALIDATED"


def test_production_schema_rejects_invalid_envelope_uuid(
    issuer_keypair,
    root_keypair,
    production_registry,
    production_schemas,
):
    signing_key, _ = issuer_keypair
    payload = authority_payload(level=3)
    envelope = signed_production_envelope(signing_key, payload)
    envelope["signatures"][0]["issuer_id"] = "not-a-uuid"
    verifier = make_verifier(production_registry, production_schemas, root_keypair)

    result = verifier.verify_authority_token(envelope, requested_level=3, inner_payload=payload)

    assert result.is_valid is False
    assert result.failure_codes == ["MALFORMED_ENVELOPE"]


def test_production_schema_rejects_missing_replay_domain(
    issuer_keypair,
    root_keypair,
    production_registry,
    production_schemas,
):
    signing_key, _ = issuer_keypair
    payload = authority_payload(level=3)
    envelope = signed_production_envelope(signing_key, payload)
    del envelope["replay_domain"]
    verifier = make_verifier(production_registry, production_schemas, root_keypair)

    result = verifier.verify_authority_token(envelope, requested_level=3, inner_payload=payload)

    assert result.is_valid is False
    assert result.failure_codes == ["MALFORMED_ENVELOPE"]


def test_production_schema_rejects_invalid_nonce_type(
    issuer_keypair,
    root_keypair,
    production_registry,
    production_schemas,
):
    signing_key, _ = issuer_keypair
    payload = authority_payload(level=3)
    envelope = signed_production_envelope(signing_key, payload)
    envelope["signatures"][0]["nonce_or_sequence"] = 12345
    verifier = make_verifier(production_registry, production_schemas, root_keypair)

    result = verifier.verify_authority_token(envelope, requested_level=3, inner_payload=payload)

    assert result.is_valid is False
    assert result.failure_codes == ["MALFORMED_ENVELOPE"]


def test_production_schema_rejects_registry_missing_signature(
    issuer_keypair,
    production_schemas,
    root_keypair,
):
    _, issuer_public_key_b64url = issuer_keypair
    _, root_public_key_b64url = root_keypair
    registry = {
        "registry_id": "00000000-0000-4000-8000-000000000000",
        "registry_version": "0.5.0",
        "registry_sequence": 1,
        "valid_from": iso_offset(-3600),
        "valid_until": iso_offset(3600),
        "last_updated": iso_offset(-60),
        "issuers": [],
        "roles": [],
    }
    registry["issuers"].append(
        {
            "issuer_id": "11111111-1111-4111-8111-111111111111",
            "key_id": "22222222-2222-4222-8222-222222222222",
            "public_key_encoding": "base64url",
            "public_key": issuer_public_key_b64url,
            "key_type": "ed25519",
            "status": "ACTIVE",
            "issued_at": iso_offset(-3600),
            "expires_at": iso_offset(3600),
            "assigned_roles": ["role-level-4-grant"],
        }
    )

    with pytest.raises(ValueError, match="Key registry failed schema validation"):
        CryptoVerifier(
            key_registry=registry,
            replay_cache=InMemoryReplayCache(),
            schemas=schema_bundle(production_schemas),
            root_public_key_b64url=root_public_key_b64url,
        )
