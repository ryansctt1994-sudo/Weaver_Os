"""Evidence gate for hardware-first integration. This does not drive a physical load."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
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


class GateRefusal(ValueError):
    """A stable admission reason; human detail is not the machine interface."""

    def __init__(self, code, detail):
        self.code = code
        super().__init__(detail)


def demand(condition, code, detail):
    if not condition:
        raise GateRefusal(code, detail)


def verify_physical_receipts(directory, policy, checkpoint_hash, bitstream_hash):
    """Pinned role keys authenticate declared observations; they cannot prove custody truth."""
    principals = {policy["author_principal"]}
    for role in REQUIRED_ROLES:
        authority = policy["authorities"][role]
        principal = authority["principal"]
        demand(
            principal and principal not in principals,
            "RECEIPT_PRINCIPAL_CONFLICT",
            "shared principal: " + role,
        )
        principals.add(principal)
        demand(
            len(bytes.fromhex(authority["custody_receipt_sha256"])) == 32,
            "RECEIPT_CUSTODY_INVALID",
            "key custody claim missing",
        )
        try:
            receipt = strict_json((directory / (role + ".json")).read_bytes())
        except FileNotFoundError as error:
            raise GateRefusal("PHYSICAL_RECEIPT_MISSING", "missing receipt: " + role) from error
        payload = receipt["payload"]
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(authority["public_key_hex"])).verify(
                base64.b64decode(receipt["signature"], validate=True),
                RECEIPT_DOMAIN + canonical(payload),
            )
        except (InvalidSignature, ValueError) as error:
            raise GateRefusal("RECEIPT_SIGNATURE_INVALID", "invalid signature: " + role) from error
        demand(
            payload["role"] == role and payload["principal"] == principal,
            "RECEIPT_IDENTITY_MISMATCH",
            "receipt role/principal mismatch",
        )
        demand(
            payload["checkpoint_sha256"] == checkpoint_hash
            and payload["bitstream_sha256"] == bitstream_hash,
            "RECEIPT_CANDIDATE_MISMATCH",
            "receipt belongs to another candidate",
        )
        demand(
            payload["custody_receipt_sha256"] == authority["custody_receipt_sha256"],
            "RECEIPT_CUSTODY_MISMATCH",
            "custody receipt mismatch",
        )
        demand(
            payload["status"] == "OBSERVED_PASS" and payload["direct_execution"] is True,
            "RECEIPT_EXECUTION_UNOBSERVED",
            "unobserved run",
        )
        demand(
            payload["board_model"] == "Arty A7-35T"
            and isinstance(payload["board_serial"], str)
            and 0 < len(payload["board_serial"]) <= 128,
            "RECEIPT_BOARD_UNIDENTIFIED",
            "unidentified board",
        )
        demand(
            all(payload["controls"].get(name) is True for name in REQUIRED_CONTROLS),
            "RECEIPT_CONTROLS_INCOMPLETE",
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
    checks, failures, bound_artifacts, refusals = {}, [], [], []

    def refuse(stage, code, error):
        code = error.code if isinstance(error, GateRefusal) else code
        detail = type(error).__name__ + ": " + str(error)
        failures.append(stage + ": " + detail)
        refusals.append({"code": code, "stage": stage, "detail": detail})

    bundle = bundle.resolve()
    checkpoint = bundle / "checkpoint.json"
    code = "ANCHOR_INVALID"
    try:
        raw = checkpoint.read_bytes()
        manifest = strict_json(raw)
        verify_anchor(
            raw,
            strict_json((bundle / "rekor-entry.json").read_bytes()),
            (bundle / "rekor-public-key.pem").read_bytes(),
        )
        checks["external_log_inclusion"] = True
        code = "CHRONICLE_INVALID"
        bound_artifacts = verify_chronicle(bundle, manifest)
        checks["anchored_chronicle_and_artifacts"] = True
    except Exception as error:
        refuse("ANCHOR_OR_CHRONICLE", code, error)
    try:
        SQLiteReplayCache(replay_db, create=False)
        checks["persistent_replay_state_present"] = True
    except Exception as error:
        refuse("REPLAY_STATE", "REPLAY_STATE_UNAVAILABLE", error)
    code = "AUTHORITY_POLICY_MISSING"
    try:
        require(
            policy_path is not None and policy_sha256 is not None,
            "external authority policy unconfigured",
        )
        code = "AUTHORITY_POLICY_UNREADABLE"
        policy_bytes = Path(policy_path).read_bytes()
        code = "AUTHORITY_POLICY_HASH_MISMATCH"
        require(
            hashlib.sha256(policy_bytes).hexdigest() == policy_sha256,
            "authority policy digest mismatch",
        )
        code = "AUTHORITY_POLICY_INVALID"
        policy = strict_json(policy_bytes)
        code = "POLICY_CANDIDATE_MISMATCH"
        require(
            hashlib.sha256(checkpoint.read_bytes()).hexdigest() == policy["checkpoint_sha256"],
            "wrong policy candidate",
        )
        code = "BITSTREAM_UNAVAILABLE"
        bitstream = bundle / "lucifer_arty_a7.bit"
        bitstream_hash = hashlib.sha256(bitstream.read_bytes()).hexdigest()
        code = "BITSTREAM_HASH_MISMATCH"
        require(bitstream_hash == policy["bitstream_sha256"], "unbound vendor bitstream")
        code = "BITSTREAM_NOT_ANCHORED"
        require(
            any(
                a["path"] == "lucifer_arty_a7.bit" and a["sha256"] == bitstream_hash
                for a in bound_artifacts
            ),
            "vendor bitstream absent from external Chronicle anchor",
        )
        code = "PHYSICAL_RECEIPTS_INVALID"
        verify_physical_receipts(
            bundle / "independent-receipts", policy, policy["checkpoint_sha256"], bitstream_hash
        )
        checks["physical_and_clean_room_receipts"] = True
    except Exception as error:
        refuse("PHYSICAL_OR_INDEPENDENT_RECEIPTS", code, error)
    return {
        "schema": "weaver-silicon-evidence-gate/1",
        "status": "READY_FOR_E3_1_REVIEW" if not failures else "NOT_READY",
        "decision": "READY" if not failures else "NOT_READY",
        "exit_code": 0 if not failures else 2,
        "reason_codes": [item["code"] for item in refusals],
        "refusals": refusals,
        "silicon_E3_1": "NOT_READY",
        "public_quorum_verified": False,
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


def main(argv=None):
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--replay-db", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--policy-sha256")
    args = parser.parse_args(argv)
    result = check_evidence(
        args.bundle, args.replay_db, policy_path=args.policy, policy_sha256=args.policy_sha256
    )
    print(json.dumps(result, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
