"""WVR-010: signing domains and payload schema versions are allowlisted, fail closed.

Two kinds of negative test live here.

* Signature-verified rejection: the cross-domain, version-confusion and unknown-value tests.
  Each envelope is signed over exactly the fields it declares, and the test asserts that the
  signature verifies before it checks the refusal. The refusal therefore comes from the
  allowlist, not from a bad signature.
* Structural rejection: the malformed-field test. Each envelope is edited after signing (a
  field deleted or replaced), so its signature no longer matches and the test says nothing
  about signatures. It shows that a missing or malformed field yields a refusal result with
  a stable code instead of an exception.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from weaver_contracts.signing_policy import (
    MALFORMED_ENVELOPE,
    SUPPORTED_SIGNING_POLICY,
    UNSUPPORTED_PAYLOAD_SCHEMA_VERSION,
    UNSUPPORTED_SIGNING_DOMAIN,
)
from weaver_runtime.replay_cache import InMemoryReplayCache
from weaver_verifier.crypto import (
    CryptoVerifier,
    build_signing_object,
    compute_payload_hash,
    verify_signature,
)

AUTHORITY_V04 = "triadic-controls:v0.4.0:authority-token"
AUTHORITY_V05 = "triadic-controls:v0.5.0:authority-token"
REFUSAL_V05 = "triadic-controls:v0.5.0:refusal-signal"

ISSUER_ID = "11111111-1111-4111-8111-111111111111"
KEY_ID = "22222222-2222-4222-8222-222222222222"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _iso(seconds: int) -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(seconds=seconds))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


@pytest.fixture
def signing_key():
    return ed25519.Ed25519PrivateKey.generate()


@pytest.fixture
def registry(signing_key):
    public = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    scopes = {
        "systems": ["rover-7"],
        "regions": ["sector-7"],
        "tasks": ["navigate"],
        "max_authority_duration_sec": 7200,
    }
    return {
        "valid_from": _iso(-3600),
        "valid_until": _iso(3600),
        "issuers": [
            {
                "issuer_id": ISSUER_ID,
                "key_id": KEY_ID,
                "public_key_encoding": "base64url",
                "public_key": _b64url(public),
                "key_type": "ed25519",
                "status": "ACTIVE",
                "issued_at": _iso(-3600),
                "expires_at": _iso(3600),
                "assigned_roles": ["role-grant", "role-refuse"],
            }
        ],
        "roles": [
            {
                "role_id": "role-grant",
                "separation_group": "group-alpha",
                "may_grant_authority": True,
                "may_revoke_or_refuse": False,
                "max_grant_level": 4,
                "can_participate_in_quorum": True,
                "allowed_scopes": dict(scopes),
            },
            {
                "role_id": "role-refuse",
                "separation_group": "group-beta",
                "may_grant_authority": False,
                "may_revoke_or_refuse": True,
                "max_grant_level": 0,
                "can_participate_in_quorum": True,
                "allowed_scopes": dict(scopes),
            },
        ],
    }


def _payload() -> dict[str, Any]:
    return {
        "token_id": "33333333-3333-4333-8333-333333333333",
        "system_id": "rover-7",
        "authority_level": 3,
        "scope": {"task": "navigate", "region": "sector-7"},
    }


def make_envelope(
    signing_key,
    *,
    payload_type: str,
    signing_domain: str,
    payload_schema_version: str,
    nonce: str,
) -> dict[str, Any]:
    """Return an envelope signed over exactly the fields it declares."""

    payload = _payload()
    envelope: dict[str, Any] = {
        "payload_type": payload_type,
        "payload_schema_version": payload_schema_version,
        "payload_hash_alg": "sha256",
        "payload_hash": compute_payload_hash(payload),
        "signing_domain": signing_domain,
        "replay_domain": {
            "system_id": "rover-7",
            "scope_hash": "b" * 64,
            "valid_from": _iso(-60),
            "valid_until": _iso(3600),
        },
        "signatures": [],
    }
    message = build_signing_object(
        signing_domain=signing_domain,
        payload_type=payload_type,
        payload_schema_version=payload_schema_version,
        payload_hash=envelope["payload_hash"],
        replay_domain=envelope["replay_domain"],
        nonce_or_sequence=nonce,
    )
    envelope["signatures"].append(
        {
            "issuer_id": ISSUER_ID,
            "key_id": KEY_ID,
            "algorithm": "ed25519",
            "signature_encoding": "base64url",
            "signature": _b64url(signing_key.sign(message)),
            "nonce_or_sequence": nonce,
            "signed_at": _iso(0),
        }
    )
    return envelope


def _verifier(registry) -> CryptoVerifier:
    return CryptoVerifier(key_registry=registry, replay_cache=InMemoryReplayCache())


def _genuine(envelope, signing_key) -> bool:
    """True when the signature verifies over the exact signing object the envelope declares."""

    message = build_signing_object(
        signing_domain=envelope["signing_domain"],
        payload_type=envelope["payload_type"],
        payload_schema_version=envelope["payload_schema_version"],
        payload_hash=envelope["payload_hash"],
        replay_domain=envelope["replay_domain"],
        nonce_or_sequence=envelope["signatures"][0]["nonce_or_sequence"],
    )
    return verify_signature(
        _b64url(signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )),
        envelope["signatures"][0]["signature"],
        message,
    )


# --- positive controls -------------------------------------------------------------


@pytest.mark.parametrize(
    "domain, version",
    [(AUTHORITY_V04, "0.4.0"), (AUTHORITY_V05, "0.5.0")],
    ids=["v0.4.0-pair", "v0.5.0-pair"],
)
def test_authority_token_is_accepted_under_each_allowlisted_pair(
    signing_key, registry, domain, version
):
    envelope = make_envelope(
        signing_key,
        payload_type="AUTHORITY_TOKEN",
        signing_domain=domain,
        payload_schema_version=version,
        nonce="n-allow-" + version,
    )
    result = _verifier(registry).verify_authority_token(
        envelope, requested_level=3, inner_payload=_payload()
    )
    assert result.is_valid, result.failure_codes


def test_refusal_signal_is_accepted_under_its_allowlisted_pair(signing_key, registry):
    envelope = make_envelope(
        signing_key,
        payload_type="REFUSAL_SIGNAL",
        signing_domain=REFUSAL_V05,
        payload_schema_version="0.5.0",
        nonce="n-refusal-ok",
    )
    result = _verifier(registry).verify_refusal_signal(
        envelope, requested_cap_level=3, inner_payload=_payload()
    )
    assert result.is_valid, result.failure_codes


# --- cross-domain reuse ------------------------------------------------------------


def test_authority_token_signed_under_the_refusal_domain_is_refused(signing_key, registry):
    """A genuine refusal-context signature must not authorize a grant."""
    envelope = make_envelope(
        signing_key,
        payload_type="AUTHORITY_TOKEN",
        signing_domain=REFUSAL_V05,
        payload_schema_version="0.5.0",
        nonce="n-cross-1",
    )
    assert _genuine(envelope, signing_key), "the refusal must come from policy, not the signature"
    result = _verifier(registry).verify_authority_token(
        envelope, requested_level=3, inner_payload=_payload()
    )
    assert not result.is_valid
    assert result.failure_codes == [UNSUPPORTED_SIGNING_DOMAIN]


def test_refusal_signal_signed_under_an_authority_domain_is_refused(signing_key, registry):
    envelope = make_envelope(
        signing_key,
        payload_type="REFUSAL_SIGNAL",
        signing_domain=AUTHORITY_V05,
        payload_schema_version="0.5.0",
        nonce="n-cross-2",
    )
    assert _genuine(envelope, signing_key)
    result = _verifier(registry).verify_refusal_signal(
        envelope, requested_cap_level=3, inner_payload=_payload()
    )
    assert not result.is_valid
    assert result.failure_codes == [UNSUPPORTED_SIGNING_DOMAIN]


# --- version confusion and unknown values --------------------------------------------


def test_version_confusion_is_refused(signing_key, registry):
    """A genuine signature for one version must not be accepted under another."""
    cases = [
        (AUTHORITY_V05, "0.4.0"),
        (AUTHORITY_V04, "0.5.0"),
    ]
    for domain, version in cases:
        envelope = make_envelope(
            signing_key,
            payload_type="AUTHORITY_TOKEN",
            signing_domain=domain,
            payload_schema_version=version,
            nonce=f"n-confuse-{domain}-{version}",
        )
        assert _genuine(envelope, signing_key)
        result = _verifier(registry).verify_authority_token(
            envelope, requested_level=3, inner_payload=_payload()
        )
        assert not result.is_valid, (domain, version)
        assert result.failure_codes == [UNSUPPORTED_PAYLOAD_SCHEMA_VERSION], (domain, version)


def test_unknown_domain_and_unknown_version_are_refused(signing_key, registry):
    unknown_domain = make_envelope(
        signing_key,
        payload_type="AUTHORITY_TOKEN",
        signing_domain="triadic-controls:v0.9.0:authority-token",
        payload_schema_version="0.9.0",
        nonce="n-unknown-domain",
    )
    assert _genuine(unknown_domain, signing_key)
    result = _verifier(registry).verify_authority_token(
        unknown_domain, requested_level=3, inner_payload=_payload()
    )
    assert result.failure_codes == [UNSUPPORTED_SIGNING_DOMAIN]

    unknown_version = make_envelope(
        signing_key,
        payload_type="AUTHORITY_TOKEN",
        signing_domain=AUTHORITY_V05,
        payload_schema_version="0.9.0",
        nonce="n-unknown-version",
    )
    assert _genuine(unknown_version, signing_key)
    result = _verifier(registry).verify_authority_token(
        unknown_version, requested_level=3, inner_payload=_payload()
    )
    assert result.failure_codes == [UNSUPPORTED_PAYLOAD_SCHEMA_VERSION]


# --- malformed fields (structural): a refusal result, never an exception ---------------

_MISSING = object()


def test_malformed_signing_fields_are_refused_with_a_result(signing_key, registry):
    """Structural rejection, not signature evidence: each envelope is edited after signing.

    No schema is supplied here, so the verifier's own check must catch these.
    """
    values = [_MISSING, None, 5, "", ["triadic-controls:v0.5.0:authority-token"]]
    for field in ("signing_domain", "payload_schema_version"):
        for value in values:
            envelope = make_envelope(
                signing_key,
                payload_type="AUTHORITY_TOKEN",
                signing_domain=AUTHORITY_V05,
                payload_schema_version="0.5.0",
                nonce=f"n-malformed-{field}-{id(value)}",
            )
            if value is _MISSING:
                del envelope[field]
            else:
                envelope[field] = value
            result = _verifier(registry).verify_authority_token(
                envelope, requested_level=3, inner_payload=_payload()
            )
            assert not result.is_valid, (field, value)
            assert result.failure_codes == [MALFORMED_ENVELOPE], (field, value)


# --- the allowlist itself ----------------------------------------------------------


def test_allowlist_is_exactly_the_reviewed_pairs():
    """Widening the policy must change this test, so the change is reviewed."""
    assert {
        payload_type: {domain: set(versions) for domain, versions in domains.items()}
        for payload_type, domains in SUPPORTED_SIGNING_POLICY.items()
    } == {
        "AUTHORITY_TOKEN": {AUTHORITY_V04: {"0.4.0"}, AUTHORITY_V05: {"0.5.0"}},
        "REFUSAL_SIGNAL": {REFUSAL_V05: {"0.5.0"}},
    }
