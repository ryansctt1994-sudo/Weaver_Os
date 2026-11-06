import copy
import json
import zipfile
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature

from triadic_controls.crypto.external_anchor import strict_json, verify_anchor
from triadic_controls.crypto.interlock_gate import check_evidence
from triadic_controls.crypto.sqlite_replay import SQLiteReplayCache

FIXTURE = Path(__file__).resolve().parents[2] / "evidence/silicon/2026-11-06"


def test_actual_public_anchor_and_rejection_of_forged_proofs():
    raw = (FIXTURE / "checkpoint.json").read_bytes()
    response = strict_json((FIXTURE / "rekor-entry.json").read_bytes())
    key = (FIXTURE / "rekor-public-key.pem").read_bytes()
    result = verify_anchor(raw, response, key)
    assert result["verification"] == "VERIFIED_LOG_INCLUSION"
    assert result["log_index"] == 3719860200
    for change in ("manifest", "body", "set", "path", "checkpoint"):
        data = copy.deepcopy(response)
        entry = next(iter(data.values()))
        candidate = raw
        if change == "manifest":
            candidate = raw + b" "
        elif change == "body":
            entry["body"] = "e30="
        elif change == "set":
            entry["verification"]["signedEntryTimestamp"] = "AAAA"
        elif change == "path":
            entry["verification"]["inclusionProof"]["hashes"][0] = "0" * 64
        else:
            entry["verification"]["inclusionProof"]["checkpoint"] = entry["verification"][
                "inclusionProof"
            ]["checkpoint"].replace("3597956049", "3597956048")
        with pytest.raises((ValueError, KeyError, InvalidSignature)):
            verify_anchor(candidate, data, key)


def test_real_bundle_cannot_qualify_without_physical_receipts(tmp_path):
    bundle = tmp_path / "bundle"
    with zipfile.ZipFile(FIXTURE / "candidate-bundle.zip") as archive:
        archive.extractall(bundle)
    db = tmp_path / "replay.db"
    SQLiteReplayCache(db)
    result = check_evidence(bundle, db)
    assert result["status"] == "NOT_READY"
    assert result["checks"] == {
        "external_log_inclusion": True,
        "anchored_chronicle_and_artifacts": True,
        "persistent_replay_state_present": True,
    }
    assert result["production_authority_earned"] is False
    assert "external authority policy unconfigured" in result["missing_or_invalid"][0]
    # Recompute a complete, internally valid Chronicle rewrite: the old external
    # checkpoint must still reject the replacement history.
    path = bundle / "qualification.chronicle.jsonl"
    entry = json.loads(path.read_text())
    entry["payload"]["silicon_observed"] = True
    import hashlib

    from triadic_controls.crypto.external_anchor import canonical

    entry["hash"] = hashlib.sha256(
        canonical({k: entry[k] for k in ("index", "timestamp", "payload", "prev_hash")})
    ).hexdigest()
    path.write_text(json.dumps(entry) + "\n")
    result = check_evidence(bundle, db)
    assert result["status"] == "NOT_READY"
    assert "anchored_chronicle_and_artifacts" not in result["checks"]


def test_role_signatures_do_not_replace_control_or_principal_checks(tmp_path):
    # Synthetic keys/claims exercise admission predicates only, not hardware evidence.
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from triadic_controls.crypto.external_anchor import canonical
    from triadic_controls.crypto.interlock_gate import (
        RECEIPT_DOMAIN,
        REQUIRED_CONTROLS,
        REQUIRED_ROLES,
        verify_physical_receipts,
    )

    policy = {"author_principal": "fixture-author", "authorities": {}}
    payloads, keys = {}, {}

    def write(role, payload):
        signature = keys[role].sign(RECEIPT_DOMAIN + canonical(payload))
        (tmp_path / (role + ".json")).write_text(
            json.dumps({"payload": payload, "signature": base64.b64encode(signature).decode()})
        )

    for role in REQUIRED_ROLES:
        keys[role] = Ed25519PrivateKey.generate()
        public = (
            keys[role]
            .public_key()
            .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
        policy["authorities"][role] = {
            "principal": role,
            "public_key_hex": public.hex(),
            "custody_receipt_sha256": "1" * 64,
        }
        payloads[role] = {
            "role": role,
            "principal": role,
            "checkpoint_sha256": "2" * 64,
            "bitstream_sha256": "3" * 64,
            "custody_receipt_sha256": "1" * 64,
            "status": "OBSERVED_PASS",
            "direct_execution": True,
            "board_model": "Arty A7-35T",
            "board_serial": "synthetic-fixture",
            "controls": dict.fromkeys(REQUIRED_CONTROLS, True),
        }
        write(role, payloads[role])
    verify_physical_receipts(tmp_path, policy, "2" * 64, "3" * 64)
    role = REQUIRED_ROLES[0]
    for field, value in (
        ("direct_execution", False),
        ("board_serial", True),
        ("bitstream_sha256", "4" * 64),
        ("principal", "fixture-author"),
    ):
        altered = dict(payloads[role], **{field: value})
        write(role, altered)
        with pytest.raises(ValueError):
            verify_physical_receipts(tmp_path, policy, "2" * 64, "3" * 64)
    altered = copy.deepcopy(payloads[role])
    altered["controls"]["effect_boundary_wired_and_observed"] = False
    write(role, altered)
    with pytest.raises(ValueError):
        verify_physical_receipts(tmp_path, policy, "2" * 64, "3" * 64)
