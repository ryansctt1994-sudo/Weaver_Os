"""CryptoVerifier core for triadic-controls TSC-001C.

This module is the pilot mathematical gatekeeper for cryptographic authority
claims. It verifies domain-separated Ed25519 signatures over canonical JSON
signing objects, checks issuer role authorization, enforces separation-group
quorum, and applies replay protection through ReplayCacheProtocol.

Important boundary: this module proves cryptographic authorization claims. It
 does not prove human legitimacy.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .replay import ReplayCacheProtocol, generate_replay_key


@dataclass
class VerificationResult:
    """Deterministic output of a cryptographic verification attempt."""

    is_valid: bool
    ledger_event_type: str
    failure_codes: List[str]
    verified_issuers: List[str]
    verification_time: str
    effective_max_authority_level: Optional[int] = None
    failure_details: Optional[str] = None
    verified_keys: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "effective_max_authority_level": self.effective_max_authority_level,
            "ledger_event_type": self.ledger_event_type,
            "failure_codes": self.failure_codes,
            "verified_issuers": self.verified_issuers,
            "verified_keys": self.verified_keys or [],
            "verification_time": self.verification_time,
            "failure_details": self.failure_details,
        }


def canonicalize_json(data: Dict[str, Any]) -> bytes:
    """RFC 8785-compatible canonical JSON serialization boundary.

    This pilot implementation enforces UTF-8 output, lexicographic key sorting,
    no insignificant whitespace, and no NaN/Infinity values. Full RFC 8785
    parity across languages should be validated with independent test vectors
    before production use.
    """

    return json.dumps(
        data,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_signing_object(
    signing_domain: str,
    payload_type: str,
    payload_schema_version: str,
    payload_hash: str,
    replay_domain: Dict[str, str],
    nonce_or_sequence: str,
) -> bytes:
    """Construct the domain-separated object issuers actually sign."""

    signing_obj = {
        "signing_domain": signing_domain,
        "payload_type": payload_type,
        "payload_schema_version": payload_schema_version,
        "payload_hash": payload_hash,
        "replay_domain": replay_domain,
        "nonce_or_sequence": nonce_or_sequence,
    }
    return canonicalize_json(signing_obj)


def _decode_base64url_nopad(data: str) -> bytes:
    """Decode base64url without padding by restoring required padding."""

    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def verify_signature(
    public_key_b64url: str,
    signature_b64url: str,
    message: bytes,
) -> bool:
    """Execute strict Ed25519 signature verification."""

    try:
        public_key_bytes = _decode_base64url_nopad(public_key_b64url)
        signature_bytes = _decode_base64url_nopad(signature_b64url)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, message)
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False


def verify_role(
    issuer_record: Dict[str, Any],
    role_policies: Dict[str, Dict[str, Any]],
    requested_level: int,
    is_refusal: bool,
) -> Tuple[bool, Optional[str]]:
    """Validate whether an issuer role authorizes the requested action."""

    for role_id in issuer_record.get("assigned_roles", []):
        policy = role_policies.get(role_id)
        if not policy:
            continue

        if is_refusal:
            if policy.get("may_revoke_or_refuse", False):
                return True, policy.get("separation_group")
        else:
            if (
                policy.get("may_grant_authority", False)
                and policy.get("max_grant_level", 0) >= requested_level
            ):
                return True, policy.get("separation_group")

    return False, None


def verify_quorum(verified_separation_groups: Set[str], requested_level: int) -> bool:
    """Enforce independent multi-signature requirements.

    Level 3 requires one independent entity. Levels 4 and 5 require two
    independent separation groups. Levels 1 and 2 require one validated issuer
    when cryptographic authorization is requested.
    """

    required_independent_groups = 2 if requested_level >= 4 else 1
    return len(verified_separation_groups) >= required_independent_groups


class CryptoVerifier:
    """Deterministic mathematical gatekeeper for triadic-controls."""

    def __init__(self, key_registry: Dict[str, Any], replay_cache: ReplayCacheProtocol):
        self.registry = key_registry
        self.replay_cache = replay_cache
        self._issuers = {
            f"{issuer['issuer_id']}|{issuer['key_id']}": issuer
            for issuer in self.registry.get("issuers", [])
        }
        self._issuer_ids = {issuer.get("issuer_id") for issuer in self.registry.get("issuers", [])}
        self._roles = {role["role_id"]: role for role in self.registry.get("roles", [])}

    def _get_iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _verify_envelope(
        self,
        envelope: Dict[str, Any],
        requested_level: int,
        is_refusal: bool,
    ) -> VerificationResult:
        now_ts = time.time()
        now_iso = self._get_iso_now()

        verified_issuers: List[str] = []
        verified_keys: List[str] = []
        verified_groups: Set[str] = set()
        failure_codes: List[str] = []

        signing_domain = envelope["signing_domain"]
        payload_type = envelope["payload_type"]
        payload_schema_version = envelope["payload_schema_version"]
        payload_hash = envelope["payload_hash"]
        replay_domain = envelope["replay_domain"]

        for sig_block in envelope.get("signatures", []):
            issuer_id = sig_block["issuer_id"]
            key_id = sig_block["key_id"]
            nonce = sig_block["nonce_or_sequence"]

            issuer_lookup = f"{issuer_id}|{key_id}"
            issuer_record = self._issuers.get(issuer_lookup)

            if not issuer_record:
                failure_codes.append(
                    "UNKNOWN_ISSUER" if issuer_id not in self._issuer_ids else "UNKNOWN_KEY"
                )
                continue

            if issuer_record.get("status") == "REVOKED":
                failure_codes.append("KEY_REVOKED")
                continue

            if issuer_record.get("status") != "ACTIVE":
                failure_codes.append("KEY_NOT_ACTIVE")
                continue

            replay_key = generate_replay_key(
                issuer_id=issuer_id,
                key_id=key_id,
                nonce_or_sequence=nonce,
                payload_type=payload_type,
                system_id=replay_domain["system_id"],
                scope_hash=replay_domain["scope_hash"],
            )

            # Pilot default. A full implementation must parse replay_domain.valid_until
            # and reject malformed or expired windows before this point.
            cache_expiry = now_ts + 3600

            if not self.replay_cache.check_and_record(replay_key, expires_at=cache_expiry):
                failure_codes.append("REPLAY_DETECTED")
                continue

            signing_message = build_signing_object(
                signing_domain=signing_domain,
                payload_type=payload_type,
                payload_schema_version=payload_schema_version,
                payload_hash=payload_hash,
                replay_domain=replay_domain,
                nonce_or_sequence=nonce,
            )

            if not verify_signature(
                public_key_b64url=issuer_record["public_key"],
                signature_b64url=sig_block["signature"],
                message=signing_message,
            ):
                failure_codes.append("INVALID_SIGNATURE")
                continue

            is_authorized, separation_group = verify_role(
                issuer_record=issuer_record,
                role_policies=self._roles,
                requested_level=requested_level,
                is_refusal=is_refusal,
            )

            if not is_authorized:
                failure_codes.append("ISSUER_ROLE_UNAUTHORIZED")
                continue

            verified_issuers.append(issuer_id)
            verified_keys.append(key_id)
            if separation_group:
                verified_groups.add(separation_group)

        if failure_codes:
            return VerificationResult(
                is_valid=False,
                effective_max_authority_level=None,
                ledger_event_type="SIGNATURE_VERIFICATION_FAILED",
                failure_codes=sorted(set(failure_codes)),
                verified_issuers=verified_issuers,
                verified_keys=verified_keys,
                verification_time=now_iso,
                failure_details="One or more signature blocks failed validation.",
            )

        if not verify_quorum(verified_groups, requested_level):
            return VerificationResult(
                is_valid=False,
                effective_max_authority_level=None,
                ledger_event_type="QUORUM_FAILED",
                failure_codes=["INSUFFICIENT_QUORUM", "QUORUM_NOT_INDEPENDENT"],
                verified_issuers=verified_issuers,
                verified_keys=verified_keys,
                verification_time=now_iso,
                failure_details="Insufficient independent organizational signatures for requested level.",
            )

        return VerificationResult(
            is_valid=True,
            effective_max_authority_level=requested_level,
            ledger_event_type=(
                "REFUSAL_SIGNATURE_VALIDATED" if is_refusal else "TOKEN_SIGNATURE_VALIDATED"
            ),
            failure_codes=[],
            verified_issuers=verified_issuers,
            verified_keys=verified_keys,
            verification_time=now_iso,
        )

    def verify_authority_token(
        self,
        envelope: Dict[str, Any],
        requested_level: int,
    ) -> VerificationResult:
        """Validate an AuthorityToken signature envelope."""

        if envelope.get("payload_type") != "AUTHORITY_TOKEN":
            return VerificationResult(
                False,
                "SIGNATURE_VERIFICATION_FAILED",
                ["SYSTEM_SCOPE_MISMATCH"],
                [],
                self._get_iso_now(),
                verified_keys=[],
            )
        return self._verify_envelope(envelope, requested_level, is_refusal=False)

    def verify_refusal_signal(
        self,
        envelope: Dict[str, Any],
        requested_cap_level: int,
    ) -> VerificationResult:
        """Validate a RefusalSignal signature envelope."""

        if envelope.get("payload_type") != "REFUSAL_SIGNAL":
            return VerificationResult(
                False,
                "SIGNATURE_VERIFICATION_FAILED",
                ["SYSTEM_SCOPE_MISMATCH"],
                [],
                self._get_iso_now(),
                verified_keys=[],
            )
        return self._verify_envelope(envelope, requested_cap_level, is_refusal=True)
