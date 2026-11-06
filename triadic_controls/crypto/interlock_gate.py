"""Evidence gate for hardware-first integration. This does not drive a physical load."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .external_anchor import canonical, require, strict_json, verify_anchor
from .sqlite_replay import SQLiteReplayCache

RECEIPT_DOMAIN = b"WEAVER-SILICON-EVIDENCE-v1\n"
REQUIRED_ROLES = ("hardware_operator", "clean_room_reviewer")
REQUIRED_CONTROLS = (
    "programmed_part_and_serial",
    "bitstream_readback_bound",
    "routed_setup_and_hold",
    "cdc_review",
    "debounce_measured",
    "software_cannot_clear_trip",
    "reset_bounce_cannot_clear_trip",
    "effect_boundary_wired_and_observed",
    "programming_and_power_custody_disclosed",
)


def verify_physical_receipts(directory, policy, checkpoint_hash, bitstream_hash):
    """Pinned role keys authenticate declared observations; they cannot prove custody truth."""
    principals = {policy["author_principal"]}
    for role in REQUIRED_ROLES:
        authority = policy["authorities"][role]
        principal = authority["principal"]
        require(principal and principal not in principals, "shared principal: " + role)
        principals.add(principal)
        require(
            len(bytes.fromhex(authority["custody_receipt_sha256"])) == 32,
            "key custody claim missing",
        )
        receipt = strict_json((directory / (role + ".json")).read_bytes())
        payload = receipt["payload"]
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(authority["public_key_hex"])).verify(
            base64.b64decode(receipt["signature"], validate=True),
            RECEIPT_DOMAIN + canonical(payload),
        )
        require(
            payload["role"] == role and payload["principal"] == principal,
            "receipt role/principal mismatch",
        )
        require(
            payload["checkpoint_sha256"] == checkpoint_hash
            and payload["bitstream_sha256"] == bitstream_hash,
            "receipt belongs to another candidate",
        )
        require(
            payload["custody_receipt_sha256"] == authority["custody_receipt_sha256"],
            "custody receipt mismatch",
        )
        require(
            payload["status"] == "OBSERVED_PASS" and payload["direct_execution"] is True,
            "unobserved run",
        )
        require(
            payload["board_model"] == "Arty A7-35T"
            and isinstance(payload["board_serial"], str)
            and 0 < len(payload["board_serial"]) <= 128,
            "unidentified board",
        )
        require(
            all(payload["controls"].get(name) is True for name in REQUIRED_CONTROLS),
            "incomplete physical controls",
        )


def verify_chronicle(bundle, manifest):
    entries = [
        strict_json(line)
        for line in (bundle / "qualification.chronicle.jsonl").read_bytes().splitlines()
    ]
    previous = "0" * 64
    for index, entry in enumerate(entries):
        require(
            entry["index"] == index and entry["prev_hash"] == previous,
            "broken Chronicle order/link",
        )
        raw = {key: entry[key] for key in ("index", "timestamp", "payload", "prev_hash")}
        # Matches the cathedral Chronicle's serialization, including ensure_ascii=True.
        require(
            hashlib.sha256(canonical(raw)).hexdigest() == entry["hash"],
            "Chronicle content mismatch",
        )
        previous = entry["hash"]
    layer = [bytes.fromhex(entry["hash"]) for entry in entries]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    root = layer[0].hex() if layer else "0" * 64
    require(
        manifest["anchor"] == {"count": len(entries), "head": previous, "merkle_root": root},
        "anchored Chronicle mismatch",
    )
    require(bool(entries), "empty candidate Chronicle")
    for artifact in entries[-1]["payload"]["artifacts"]:
        path = (bundle / artifact["path"]).resolve()
        require(path.is_relative_to(bundle.resolve()), "artifact traversal")
        require(
            hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"],
            "candidate artifact mismatch",
        )
    return entries[-1]["payload"]["artifacts"]


def check_evidence(bundle: Path, replay_db: Path, *, policy_path=None, policy_sha256=None):
    """Return NOT_READY on any missing, untrusted or mismatched prerequisite."""
    checks, failures, bound_artifacts = {}, [], []
    bundle = bundle.resolve()
    checkpoint = bundle / "checkpoint.json"
    try:
        raw = checkpoint.read_bytes()
        manifest = strict_json(raw)
        verify_anchor(
            raw,
            strict_json((bundle / "rekor-entry.json").read_bytes()),
            (bundle / "rekor-public-key.pem").read_bytes(),
        )
        checks["external_log_inclusion"] = True
        bound_artifacts = verify_chronicle(bundle, manifest)
        checks["anchored_chronicle_and_artifacts"] = True
    except Exception as error:
        failures.append("ANCHOR_OR_CHRONICLE: " + type(error).__name__ + ": " + str(error))
    try:
        SQLiteReplayCache(replay_db, create=False)
        checks["persistent_replay_state_present"] = True
    except Exception as error:
        failures.append("REPLAY_STATE: " + type(error).__name__ + ": " + str(error))
    try:
        require(
            policy_path is not None and policy_sha256 is not None,
            "external authority policy unconfigured",
        )
        policy_bytes = Path(policy_path).read_bytes()
        require(
            hashlib.sha256(policy_bytes).hexdigest() == policy_sha256,
            "authority policy digest mismatch",
        )
        policy = strict_json(policy_bytes)
        require(
            hashlib.sha256(checkpoint.read_bytes()).hexdigest() == policy["checkpoint_sha256"],
            "wrong policy candidate",
        )
        bitstream = bundle / "lucifer_arty_a7.bit"
        bitstream_hash = hashlib.sha256(bitstream.read_bytes()).hexdigest()
        require(bitstream_hash == policy["bitstream_sha256"], "unbound vendor bitstream")
        require(
            any(
                a["path"] == "lucifer_arty_a7.bit" and a["sha256"] == bitstream_hash
                for a in bound_artifacts
            ),
            "vendor bitstream absent from external Chronicle anchor",
        )
        verify_physical_receipts(
            bundle / "independent-receipts", policy, policy["checkpoint_sha256"], bitstream_hash
        )
        checks["physical_and_clean_room_receipts"] = True
    except Exception as error:
        failures.append(
            "PHYSICAL_OR_INDEPENDENT_RECEIPTS: " + type(error).__name__ + ": " + str(error)
        )
    return {
        "schema": "weaver-silicon-evidence-gate/1",
        "status": "READY_FOR_E3_1_REVIEW" if not failures else "NOT_READY",
        "checks": checks,
        "missing_or_invalid": failures,
        "production_authority_earned": False,
        "scope": (
            "Deployment evidence gate; live effect prevention must be physically wired. "
            "Named principal/custody claims require external review."
        ),
    }


def build_evidence_gated_verifier(
    *, bundle, replay_db, policy_path, policy_sha256, key_registry, **kwargs
):
    """Opt-in integration with the existing CryptoVerifier; no missing-state fallback."""
    decision = check_evidence(
        Path(bundle), Path(replay_db), policy_path=policy_path, policy_sha256=policy_sha256
    )
    if decision["status"] != "READY_FOR_E3_1_REVIEW":
        raise ValueError("Silicon evidence NOT_READY: " + "; ".join(decision["missing_or_invalid"]))
    from .verifier import CryptoVerifier

    return CryptoVerifier(
        key_registry=key_registry, replay_cache=SQLiteReplayCache(replay_db, create=False), **kwargs
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--replay-db", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--policy-sha256")
    args = parser.parse_args()
    result = check_evidence(
        args.bundle, args.replay_db, policy_path=args.policy, policy_sha256=args.policy_sha256
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "READY_FOR_E3_1_REVIEW" else 2)
