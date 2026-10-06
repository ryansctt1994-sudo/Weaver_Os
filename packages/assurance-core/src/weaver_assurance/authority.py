"""Ed25519 authority envelopes with role, quorum, scope, and replay checks."""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_json, sha256_json
from .replay import SQLiteReplayCache


DOMAIN = "weaver.assurance.authority-envelope.v1"


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


@dataclass(frozen=True)
class SignatureBlock:
    key_id: str
    signature: str


@dataclass(frozen=True)
class KeyGrant:
    key_id: str
    public_key: str
    separation_group: str
    max_authority: int
    valid_from: int
    valid_until: int
    allowed_actions: tuple[str, ...] = ("*",)


@dataclass(frozen=True)
class AuthorityEnvelope:
    version: str
    envelope_id: str
    issuer: str
    subject: str
    action: str
    system_id: str
    scope_hash: str
    nonce: str
    issued_at: int
    valid_until: int
    requested_authority: int
    payload: dict[str, Any]
    payload_hash: str
    signatures: tuple[SignatureBlock, ...] = ()

    def signing_object(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("signatures")
        value["signing_domain"] = DOMAIN
        return value


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    reason_codes: tuple[str, ...]
    verified_keys: tuple[str, ...] = ()
    verified_groups: tuple[str, ...] = ()
    replay_key: str | None = None


def create_envelope(
    *,
    envelope_id: str,
    issuer: str,
    subject: str,
    action: str,
    system_id: str,
    scope_hash: str,
    nonce: str,
    issued_at: int,
    valid_until: int,
    requested_authority: int,
    payload: dict[str, Any],
) -> AuthorityEnvelope:
    return AuthorityEnvelope(
        version="weaver.assurance.envelope.v1",
        envelope_id=envelope_id,
        issuer=issuer,
        subject=subject,
        action=action,
        system_id=system_id,
        scope_hash=scope_hash,
        nonce=nonce,
        issued_at=int(issued_at),
        valid_until=int(valid_until),
        requested_authority=int(requested_authority),
        payload=payload,
        payload_hash=sha256_json(payload),
    )


def sign_envelope(envelope: AuthorityEnvelope, key_id: str, private_key: Ed25519PrivateKey) -> AuthorityEnvelope:
    signature = private_key.sign(canonical_json(envelope.signing_object()))
    block = SignatureBlock(key_id=key_id, signature=_b64_encode(signature))
    return replace(envelope, signatures=envelope.signatures + (block,))


def public_key_b64(private_key: Ed25519PrivateKey) -> str:
    return _b64_encode(private_key.public_key().public_bytes_raw())


class AuthorityVerifier:
    def __init__(self, grants: Iterable[KeyGrant], replay_cache: SQLiteReplayCache) -> None:
        self.grants = {grant.key_id: grant for grant in grants}
        self.replay_cache = replay_cache

    @staticmethod
    def replay_key(envelope: AuthorityEnvelope) -> str:
        raw = "|".join(
            (
                envelope.system_id,
                envelope.scope_hash,
                envelope.issuer,
                envelope.nonce,
                envelope.action,
                envelope.payload_hash,
            )
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify(self, envelope: AuthorityEnvelope, *, now: int | None = None) -> VerificationResult:
        current = int(time.time()) if now is None else int(now)
        errors: list[str] = []

        if envelope.version != "weaver.assurance.envelope.v1":
            errors.append("UNSUPPORTED_VERSION")
        if not all(
            (envelope.envelope_id, envelope.issuer, envelope.subject, envelope.action, envelope.system_id,
             envelope.scope_hash, envelope.nonce)
        ):
            errors.append("MISSING_REQUIRED_FIELD")
        if envelope.payload_hash != sha256_json(envelope.payload):
            errors.append("PAYLOAD_HASH_MISMATCH")
        if envelope.issued_at > current or current >= envelope.valid_until or envelope.issued_at >= envelope.valid_until:
            errors.append("TIME_WINDOW_INVALID")
        if not 0 <= envelope.requested_authority <= 6:
            errors.append("AUTHORITY_LEVEL_INVALID")
        if errors:
            return VerificationResult(False, tuple(sorted(set(errors))))

        verified_keys: list[str] = []
        groups: set[str] = set()
        message = canonical_json(envelope.signing_object())

        for block in envelope.signatures:
            grant = self.grants.get(block.key_id)
            if grant is None or block.key_id in verified_keys:
                continue
            # A signature grant must cover the envelope's entire lifetime. If
            # only issuance were checked, an envelope could outlive the key
            # grant that authorized it.
            if not (
                grant.valid_from <= envelope.issued_at
                and envelope.valid_until <= grant.valid_until
            ):
                continue
            if grant.max_authority < envelope.requested_authority:
                continue
            if "*" not in grant.allowed_actions and envelope.action not in grant.allowed_actions:
                continue
            try:
                Ed25519PublicKey.from_public_bytes(_b64_decode(grant.public_key)).verify(
                    _b64_decode(block.signature), message
                )
            except (ValueError, InvalidSignature):
                continue
            verified_keys.append(block.key_id)
            groups.add(grant.separation_group)

        required_groups = 2 if envelope.requested_authority >= 4 else 1
        if len(groups) < required_groups:
            return VerificationResult(
                False,
                ("QUORUM_NOT_MET",),
                tuple(sorted(verified_keys)),
                tuple(sorted(groups)),
            )

        replay_key = self.replay_key(envelope)
        if not self.replay_cache.check_and_record(replay_key, envelope.valid_until, now=current):
            return VerificationResult(
                False,
                ("REPLAY_DETECTED",),
                tuple(sorted(verified_keys)),
                tuple(sorted(groups)),
                replay_key,
            )

        return VerificationResult(
            True,
            ("AUTHORIZED",),
            tuple(sorted(verified_keys)),
            tuple(sorted(groups)),
            replay_key,
        )
