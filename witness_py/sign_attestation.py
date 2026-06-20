#!/usr/bin/env python3
"""Create a witness attestation payload for an E3.5 replay result.

This module intentionally leaves key loading to the operator. The private key
must be supplied by the witness environment, never committed to the repository.
"""

import base64
import json
from datetime import datetime, timezone
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_attestation(
    *,
    witness_id: str,
    public_key_id: str,
    sequence_number: int,
    head_hash: str,
    state_digest: str,
) -> dict[str, Any]:
    return {
        "witness_id": witness_id,
        "public_key_id": public_key_id,
        "sequence_number": sequence_number,
        "head_hash": head_hash,
        "state_digest": state_digest,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def sign_attestation(attestation: dict[str, Any], private_key: Any) -> dict[str, Any]:
    """Sign a canonical attestation object.

    The private_key object must expose a sign(bytes) -> bytes method, such as
    Ed25519 private keys from cryptography or compatible libraries.
    """
    signature = private_key.sign(canonical_json(attestation))
    signed = dict(attestation)
    signed["signature"] = base64.b64encode(signature).decode("ascii")
    return signed
