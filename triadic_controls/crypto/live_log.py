"""Fetch Rekor's own checkpoint and connect the retained proof to it (read-only)."""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .external_anchor import LOG_KEY_ID, require, strict_json, verify_anchor


def verify_checkpoint(note, public_key):
    key = serialization.load_pem_public_key(public_key)
    der = key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    require(hashlib.sha256(der).hexdigest() == LOG_KEY_ID, "unpinned service key")
    text, signatures = note.split("\n\n", 1)
    lines = text.splitlines()
    require(len(lines) == 3 and lines[0].startswith("rekor.sigstore.dev - "), "wrong origin")
    size = int(lines[1])
    root = base64.b64decode(lines[2], validate=True)
    require(size > 0 and len(root) == 32, "invalid checkpoint")
    valid = False
    for line in signatures.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[:2] == ["—", "rekor.sigstore.dev"]:
            signature = base64.b64decode(fields[2], validate=True)
            if signature[:4] == bytes.fromhex(LOG_KEY_ID)[:4]:
                key.verify(signature[4:], (text + "\n").encode(), ec.ECDSA(hashes.SHA256()))
                valid = True
    require(valid, "missing checkpoint signature")
    return lines[0].split(" - ")[1], size, root.hex()


def verify_consistency(first_size, last_size, first_root, last_root, encoded_proof):
    require(
        type(first_size) is int and type(last_size) is int and 0 < first_size <= last_size,
        "invalid consistency sizes",
    )
    old, new = bytes.fromhex(first_root), bytes.fromhex(last_root)
    require(len(old) == len(new) == 32, "invalid roots")
    proof = [bytes.fromhex(value) for value in encoded_proof]
    require(all(len(value) == 32 for value in proof), "invalid proof hash")
    if first_size == last_size:
        require(not proof and old == new, "same-size checkpoint mismatch")
        return
    fn, sn = first_size - 1, last_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    if fn == 0:
        fr = sr = old
    else:
        require(bool(proof), "missing consistency proof")
        fr = sr = proof.pop(0)
    for sibling in proof:
        require(sn != 0, "excess consistency proof")
        if fn & 1 or fn == sn:
            fr = hashlib.sha256(b"\x01" + sibling + fr).digest()
            sr = hashlib.sha256(b"\x01" + sibling + sr).digest()
            while fn != 0 and not fn & 1:
                fn >>= 1
                sn >>= 1
        else:
            sr = hashlib.sha256(b"\x01" + sr + sibling).digest()
        fn >>= 1
        sn >>= 1
    require(sn == 0 and fr == old and sr == new, "consistency proof mismatch")


def audit(manifest, entry, expected_sha256, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    observations = []

    def fetch(url, name):
        request = urllib.request.Request(url, headers={"User-Agent": "weaver-live-log-audit/1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, "oversized API response")
            observations.append(
                {
                    "url": url,
                    "http_status": response.status,
                    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
        (output / name).write_bytes(raw)
        return raw

    try:
        raw = Path(manifest).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected_sha256, "unexpected checkpoint digest")
        key = fetch("https://rekor.sigstore.dev/api/v1/log/publicKey", "service-key-response.txt")
        if key.startswith(b'"'):
            key = strict_json(key).encode()
        (output / "service-public-key.pem").write_bytes(key)
        retained = strict_json(Path(entry).read_bytes())
        prior = verify_anchor(raw, retained, key)
        proof = next(iter(retained.values()))["verification"]["inclusionProof"]
        shard = str(int(prior["uuid"][:16], 16))
        url = "https://rekor.sigstore.dev/api/v1/log?" + urllib.parse.urlencode({"treeID": shard})
        live = strict_json(fetch(url, "live-log.json"))
        tree, size, root = verify_checkpoint(live["signedTreeHead"], key)
        require(
            tree == shard == live["treeID"]
            and size == live["treeSize"]
            and root == live["rootHash"],
            "live checkpoint metadata mismatch",
        )
        query = urllib.parse.urlencode(
            {"firstSize": proof["treeSize"], "lastSize": size, "treeID": shard}
        )
        consistency = strict_json(
            fetch("https://rekor.sigstore.dev/api/v1/log/proof?" + query, "consistency-proof.json")
        )
        verify_consistency(proof["treeSize"], size, proof["rootHash"], root, consistency["hashes"])
        result = {
            "status": "VERIFIED_LIVE_CHECKPOINT_CONNECTION",
            "reason_codes": [],
            "checkpoint_sha256": expected_sha256,
            "entry_url": prior["entry_url"],
            "bundled_tree_size": proof["treeSize"],
            "bundled_root": proof["rootHash"],
            "live_tree_size": size,
            "live_root": root,
            "tree_id": tree,
            "signed_live_checkpoint_verified": True,
            "consistency_verified": True,
            "proof_response_rootHash": consistency.get("rootHash"),
            "proof_root_policy": "Recompute both roots; compare signed checkpoints. "
            "Unsigned response rootHash is not an acceptance input.",
        }
    except Exception as error:
        result = {
            "status": "INCONCLUSIVE",
            "reason_codes": ["LIVE_LOG_CHECK_FAILED"],
            "detail": type(error).__name__ + ": " + str(error),
        }
    result.update(
        {
            "schema": "rekor-live-checkpoint-audit/1",
            "observations": observations,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "independent_observer": False,
            "route": "Direct Rekor HTTPS API, same principal",
            "execution_or_compilation_proved": False,
            "silicon_E3_1": "NOT_READY",
            "full_TUF_chain_verified": False,
            "production_authority_earned": False,
        }
    )
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--entry", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.manifest, args.entry, args.checkpoint_sha256, args.output)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "VERIFIED_LIVE_CHECKPOINT_CONNECTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
