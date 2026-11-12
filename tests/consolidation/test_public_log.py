from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from weaver_verifier.public_log import PublicLogProofError, verify_publication

FIXTURES = Path(__file__).parents[1] / "fixtures" / "consolidation" / "rekor"


def inputs():
    return tuple(
        (FIXTURES / name).read_bytes()
        for name in ("checkpoint.json", "rekor-entry.json", "rekor-public-key.pem")
    )


def test_retained_publication_proof_verifies_without_hardware_or_authority_claim():
    result = verify_publication(*inputs())
    assert result["verification"] == "VERIFIED_LOG_INCLUSION"
    assert result["independent_hardware_observation"] is False
    assert "Full TUF chain not verified" in result["trust_bootstrap"]


@pytest.mark.parametrize("damage", ["manifest", "key", "root", "sibling", "log-id", "time"])
def test_tampering_never_verifies(damage):
    manifest, raw, key = inputs()
    entry = json.loads(raw)
    row = next(iter(entry.values()))
    if damage == "manifest":
        manifest += b" "
    elif damage == "key":
        key = b"not a public key"
    elif damage == "root":
        row["verification"]["inclusionProof"]["rootHash"] = "00" * 32
    elif damage == "sibling":
        row["verification"]["inclusionProof"]["hashes"][0] = "00" * 32
    elif damage == "log-id":
        row["logID"] = "00" * 32
    else:
        row["integratedTime"] += 1
    with pytest.raises((PublicLogProofError, InvalidSignature)):
        verify_publication(manifest, json.dumps(entry).encode(), key)


@pytest.mark.parametrize(
    "raw", [b"[]", b"null", b"{}", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b"[" * 16000]
)
def test_malformed_proof_is_a_controlled_refusal(raw):
    manifest, _, key = inputs()
    with pytest.raises(PublicLogProofError):
        verify_publication(manifest, raw, key)


def test_proof_size_is_bounded():
    manifest, _, key = inputs()
    with pytest.raises(PublicLogProofError, match="1 MiB"):
        verify_publication(manifest, b" " * (1024 * 1024 + 1), key)


def test_another_valid_public_key_does_not_replace_the_pinned_log_key():
    manifest, entry, _ = inputs()
    key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    with pytest.raises(PublicLogProofError, match="unpinned log key"):
        verify_publication(manifest, entry, key)


@pytest.mark.parametrize("field", ["signedEntryTimestamp", "checkpoint"])
def test_each_log_signature_is_checked(field):
    manifest, raw, key = inputs()
    entry = json.loads(raw)
    verification = next(iter(entry.values()))["verification"]
    if field == "signedEntryTimestamp":
        signature = bytearray(base64.b64decode(verification[field]))
        signature[-1] ^= 1
        verification[field] = base64.b64encode(signature).decode()
    else:
        checkpoint = verification["inclusionProof"]["checkpoint"]
        text, signatures = checkpoint.split("\n\n", 1)
        fields = signatures.strip().split()
        signature = bytearray(base64.b64decode(fields[-1]))
        signature[-1] ^= 1
        fields[-1] = base64.b64encode(signature).decode()
        verification["inclusionProof"]["checkpoint"] = text + "\n\n" + " ".join(fields) + "\n"
    with pytest.raises(PublicLogProofError):
        verify_publication(manifest, json.dumps(entry).encode(), key)
