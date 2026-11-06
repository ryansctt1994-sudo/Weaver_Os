"""Offline Rekor checkpoint verification. A public log receipt is not a hardware test."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

LOG_KEY_ID = "c0d23d6ad406973f9559f3ba2d1ca01f84147d8ffc5b8445c224f98b9591801d"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def strict_json(raw):
    return json.loads(raw, object_pairs_hook=_pairs)


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def verify_merkle(body, proof):
    index, size = proof["logIndex"], proof["treeSize"]
    require(type(index) is int and type(size) is int and 0 <= index < size, "invalid Merkle bounds")
    node = hashlib.sha256(b"\x00" + body).digest()
    leaf = node.hex()
    fn, sn = index, size - 1
    for encoded in proof["hashes"]:
        require(sn != 0, "excess Merkle path")
        sibling = bytes.fromhex(encoded)
        require(len(sibling) == 32, "invalid Merkle sibling")
        if (fn & 1) or fn == sn:
            node = hashlib.sha256(b"\x01" + sibling + node).digest()
            while fn != 0 and not fn & 1:
                fn >>= 1
                sn >>= 1
        else:
            node = hashlib.sha256(b"\x01" + node + sibling).digest()
        fn >>= 1
        sn >>= 1
    require(sn == 0 and node.hex() == proof["rootHash"], "Merkle inclusion mismatch")
    return leaf


def verify_anchor(manifest_bytes, response, pinned_log_key_pem):
    """Verify author signature, SET, inclusion, signed checkpoint and pinned log ID."""
    require(len(response) == 1, "expected exactly one Rekor entry")
    uuid, entry = next(iter(response.items()))
    key = serialization.load_pem_public_key(pinned_log_key_pem)
    require(isinstance(key, ec.EllipticCurvePublicKey), "unexpected log key type")
    der = key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    require(hashlib.sha256(der).hexdigest() == LOG_KEY_ID == entry["logID"], "unpinned log key")
    require(
        type(entry["integratedTime"]) is int and entry["integratedTime"] > 0,
        "invalid integrated time",
    )
    require(type(entry["logIndex"]) is int and entry["logIndex"] >= 0, "invalid global index")
    body = base64.b64decode(entry["body"], validate=True)
    record = strict_json(body)
    require(
        record["kind"] == "hashedrekord" and record["apiVersion"] == "0.0.1",
        "unsupported entry kind",
    )
    hashed = record["spec"]["data"]["hash"]
    require(
        hashed["algorithm"] == "sha256"
        and hashed["value"] == hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest digest mismatch",
    )
    author = record["spec"]["signature"]
    public = serialization.load_pem_public_key(
        base64.b64decode(author["publicKey"]["content"], validate=True)
    )
    require(isinstance(public, ec.EllipticCurvePublicKey), "unsupported author key")
    public.verify(
        base64.b64decode(author["content"], validate=True),
        manifest_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    signed = {name: entry[name] for name in ("body", "integratedTime", "logID", "logIndex")}
    verification = entry["verification"]
    key.verify(
        base64.b64decode(verification["signedEntryTimestamp"], validate=True),
        canonical(signed),
        ec.ECDSA(hashes.SHA256()),
    )
    proof = verification["inclusionProof"]
    leaf = verify_merkle(body, proof)
    checkpoint = proof["checkpoint"]
    text, signatures = checkpoint.split("\n\n", 1)
    lines = text.splitlines()
    require(len(lines) == 3 and lines[0].startswith("rekor.sigstore.dev - "), "checkpoint origin")
    require(
        int(lines[1]) == proof["treeSize"]
        and base64.b64decode(lines[2], validate=True).hex() == proof["rootHash"],
        "checkpoint tree mismatch",
    )
    signed_checkpoint = (text + "\n").encode("utf-8")
    valid = False
    for line in signatures.splitlines():
        fields = line.split()
        if len(fields) != 3 or fields[:2] != ["—", "rekor.sigstore.dev"]:
            continue
        signature = base64.b64decode(fields[2], validate=True)
        if signature[:4] == bytes.fromhex(LOG_KEY_ID)[:4]:
            key.verify(signature[4:], signed_checkpoint, ec.ECDSA(hashes.SHA256()))
            valid = True
    require(valid, "missing pinned checkpoint signature")
    require(
        len(uuid) == 80
        and uuid[-64:] == leaf
        and int(uuid[:16], 16) == int(lines[0].split(" - ")[1]),
        "UUID/shard/leaf mismatch",
    )
    return {
        "schema": "chronicle-rekor-verification/1",
        "verification": "VERIFIED_LOG_INCLUSION",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "uuid": uuid,
        "entry_url": "https://rekor.sigstore.dev/api/v1/log/entries/" + uuid,
        "integrated_time": entry["integratedTime"],
        "log_index": entry["logIndex"],
        "shard_log_index": proof["logIndex"],
        "tree_size": proof["treeSize"],
        "root_hash": proof["rootHash"],
        "log_key_id": LOG_KEY_ID,
        "independent_hardware_observation": False,
        "trust_bootstrap": (
            "Pinned key matched HTTPS official Sigstore trusted_root and log publicKey. "
            "Full TUF chain not verified."
        ),
        "limits": (
            "One log inclusion/checkpoint; no hardware behavior, event truth, witness "
            "independence, future consistency or fork immunity proved."
        ),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("entry", type=Path)
    parser.add_argument("log_key", type=Path)
    args = parser.parse_args()
    result = verify_anchor(
        args.manifest.read_bytes(), strict_json(args.entry.read_bytes()), args.log_key.read_bytes()
    )
    print(json.dumps(result, indent=2))
