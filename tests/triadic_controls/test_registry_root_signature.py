import base64
import copy
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from triadic_controls.crypto.replay import InMemoryReplayCache
from triadic_controls.crypto.verifier import CryptoVerifier, canonicalize_json


def b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def iso_offset(seconds: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=seconds)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")


def generate_keypair():
    signing_key = ed25519.Ed25519PrivateKey.generate()
    public_key = signing_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return signing_key, b64url_nopad(public_key_bytes)


def unsigned_registry(issuer_public_key_b64url: str) -> dict:
    return {
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
                "description": "Root signature test role.",
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


def sign_registry(registry: dict, root_signing_key) -> dict:
    signed = copy.deepcopy(registry)
    signature = root_signing_key.sign(canonicalize_json(signed))
    signed["registry_signature"] = b64url_nopad(signature)
    return signed


def test_valid_root_signature_allows_verifier_instantiation():
    root_signing_key, root_public_key = generate_keypair()
    _, issuer_public_key = generate_keypair()
    registry = sign_registry(unsigned_registry(issuer_public_key), root_signing_key)

    verifier = CryptoVerifier(
        key_registry=registry,
        replay_cache=InMemoryReplayCache(),
        root_public_key_b64url=root_public_key,
    )

    assert verifier.registry["registry_version"] == "0.5.0"


def test_tampered_registry_rejected_after_root_signature():
    root_signing_key, root_public_key = generate_keypair()
    _, issuer_public_key = generate_keypair()
    registry = sign_registry(unsigned_registry(issuer_public_key), root_signing_key)
    registry["roles"][0]["max_grant_level"] = 5

    with pytest.raises(ValueError, match="root signature verification"):
        CryptoVerifier(
            key_registry=registry,
            replay_cache=InMemoryReplayCache(),
            root_public_key_b64url=root_public_key,
        )


def test_wrong_root_key_rejected():
    root_signing_key, _ = generate_keypair()
    _, wrong_root_public_key = generate_keypair()
    _, issuer_public_key = generate_keypair()
    registry = sign_registry(unsigned_registry(issuer_public_key), root_signing_key)

    with pytest.raises(ValueError, match="root signature verification"):
        CryptoVerifier(
            key_registry=registry,
            replay_cache=InMemoryReplayCache(),
            root_public_key_b64url=wrong_root_public_key,
        )


def test_missing_registry_signature_rejected_when_root_key_required():
    _, root_public_key = generate_keypair()
    _, issuer_public_key = generate_keypair()
    registry = unsigned_registry(issuer_public_key)

    with pytest.raises(ValueError, match="root signature verification"):
        CryptoVerifier(
            key_registry=registry,
            replay_cache=InMemoryReplayCache(),
            root_public_key_b64url=root_public_key,
        )
