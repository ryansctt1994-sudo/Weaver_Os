"""Complete synthetic trust domain: real crypto/checks, no board observations."""

import base64
import copy
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

from triadic_controls.crypto import external_anchor
from triadic_controls.crypto import interlock_gate as gate
from triadic_controls.crypto.external_anchor import canonical
from triadic_controls.crypto.sqlite_replay import SQLiteReplayCache


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def b64(raw):
    return base64.b64encode(raw).decode()


@pytest.fixture
def complete_gate_control(tmp_path, monkeypatch):
    # Patch the test trust root only. Every signature/inclusion/policy check runs.
    # No production pin override or fixture-acceptance switch is added.
    bundle = tmp_path / "synthetic-bundle"
    bundle.mkdir()
    bitstream = b"SYNTHETIC CONTROL ONLY; not an FPGA bitstream or physical observation\n"
    (bundle / "lucifer_arty_a7.bit").write_bytes(bitstream)
    entry = {
        "index": 0,
        "timestamp": 1,
        "prev_hash": "0" * 64,
        "payload": {
            "fixture_kind": "SYNTHETIC_GATE_CONTROL",
            "artifacts": [{"path": "lucifer_arty_a7.bit", "sha256": digest(bitstream)}],
        },
    }
    entry["hash"] = digest(canonical(entry))
    (bundle / "qualification.chronicle.jsonl").write_bytes(canonical(entry) + b"\n")
    checkpoint = canonical(
        {
            "anchor": {"count": 1, "head": entry["hash"], "merkle_root": entry["hash"]},
            "fixture_kind": "SYNTHETIC_GATE_CONTROL",
        }
    )
    (bundle / "checkpoint.json").write_bytes(checkpoint)
    log = ec.generate_private_key(ec.SECP256R1())
    author = ec.generate_private_key(ec.SECP256R1())

    def pem(key):
        return key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    log_id = digest(
        log.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    monkeypatch.setattr(external_anchor, "LOG_KEY_ID", log_id)
    record = {
        "kind": "hashedrekord",
        "apiVersion": "0.0.1",
        "spec": {
            "data": {"hash": {"algorithm": "sha256", "value": digest(checkpoint)}},
            "signature": {
                "content": b64(author.sign(checkpoint, ec.ECDSA(hashes.SHA256()))),
                "publicKey": {"content": b64(pem(author))},
            },
        },
    }
    body = canonical(record)
    leaf = hashlib.sha256(b"\x00" + body).digest()
    text = "rekor.sigstore.dev - 7\n1\n" + b64(leaf) + "\n"
    note_signature = bytes.fromhex(log_id)[:4] + log.sign(text.encode(), ec.ECDSA(hashes.SHA256()))
    response_entry = {"body": b64(body), "integratedTime": 1, "logID": log_id, "logIndex": 0}
    signature = log.sign(canonical(response_entry), ec.ECDSA(hashes.SHA256()))
    response_entry["verification"] = {
        "signedEntryTimestamp": b64(signature),
        "inclusionProof": {
            "logIndex": 0,
            "treeSize": 1,
            "rootHash": leaf.hex(),
            "hashes": [],
            "checkpoint": text + "\n— rekor.sigstore.dev " + b64(note_signature) + "\n",
        },
    }
    (bundle / "rekor-entry.json").write_bytes(
        canonical({"0000000000000007" + leaf.hex(): response_entry})
    )
    (bundle / "rekor-public-key.pem").write_bytes(pem(log))
    policy = {
        "author_principal": "SYNTHETIC-author",
        "checkpoint_sha256": digest(checkpoint),
        "bitstream_sha256": digest(bitstream),
        "authorities": {},
    }
    receipts = bundle / "independent-receipts"
    receipts.mkdir()
    keys, payloads = {}, {}
    for role in gate.REQUIRED_ROLES:
        key = ed25519.Ed25519PrivateKey.generate()
        keys[role] = key
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        policy["authorities"][role] = {
            "principal": "SYNTHETIC-" + role,
            "public_key_hex": public.hex(),
            "custody_receipt_sha256": "1" * 64,
        }
        payload = {
            "role": role,
            "principal": "SYNTHETIC-" + role,
            "checkpoint_sha256": digest(checkpoint),
            "bitstream_sha256": digest(bitstream),
            "custody_receipt_sha256": "1" * 64,
            "status": "OBSERVED_PASS",
            "direct_execution": True,
            "board_model": "Arty A7-35T",
            "board_serial": "SYNTHETIC-NO-BOARD",
            "controls": dict.fromkeys(gate.REQUIRED_CONTROLS, True),
        }
        payloads[role] = payload
        (receipts / (role + ".json")).write_bytes(
            canonical(
                {
                    "payload": payload,
                    "signature": b64(key.sign(gate.RECEIPT_DOMAIN + canonical(payload))),
                }
            )
        )
    policy_path = tmp_path / "test-policy.json"
    policy_path.write_bytes(canonical(policy))
    db = tmp_path / "test-replay.db"
    SQLiteReplayCache(db)
    return {
        "bundle": bundle,
        "db": db,
        "policy": policy_path,
        "keys": keys,
        "payloads": payloads,
        "log_key_id": log_id,
    }


def run_control(control, capsys):
    args = ["--bundle", str(control["bundle"]), "--replay-db", str(control["db"])]
    if control.get("policy"):
        args += [
            "--policy",
            str(control["policy"]),
            "--policy-sha256",
            digest(control["policy"].read_bytes()),
        ]
    code = gate.main(args)
    return code, json.loads(capsys.readouterr().out)


def test_full_gate_positive_control_and_cli(complete_gate_control, capsys):
    code, result = run_control(complete_gate_control, capsys)
    assert code == result["exit_code"] == 0
    assert result["decision"] == "READY"
    assert result["status"] == "READY_FOR_E3_1_REVIEW"
    assert result["reason_codes"] == result["refusals"] == []
    assert all(result["checks"].values()) and len(result["checks"]) == 4
    assert result["production_authority_earned"] is False
    assert result["silicon_E3_1"] == "NOT_READY"
    assert result["public_quorum_verified"] is False


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("policy", "AUTHORITY_POLICY_MISSING"),
        ("cache", "REPLAY_STATE_UNAVAILABLE"),
        ("bitstream", "BITSTREAM_HASH_MISMATCH"),
        ("signature", "RECEIPT_SIGNATURE_INVALID"),
        ("control", "RECEIPT_CONTROLS_INCOMPLETE"),
        ("anchor", "ANCHOR_INVALID"),
    ],
)
def test_single_failed_prerequisite_refuses(complete_gate_control, capsys, mutation, expected):
    c = complete_gate_control
    role = gate.REQUIRED_ROLES[0]
    receipt = c["bundle"] / "independent-receipts" / (role + ".json")
    if mutation == "policy":
        c["policy"] = None
    elif mutation == "cache":
        c["db"].unlink()
    elif mutation == "bitstream":
        (c["bundle"] / "lucifer_arty_a7.bit").write_bytes(b"different")
    elif mutation == "signature":
        data = json.loads(receipt.read_text())
        data["signature"] = b64(bytes(64))
        receipt.write_bytes(canonical(data))
    elif mutation == "control":
        payload = copy.deepcopy(c["payloads"][role])
        payload["controls"]["software_cannot_clear_trip"] = False
        receipt.write_bytes(
            canonical(
                {
                    "payload": payload,
                    "signature": b64(
                        c["keys"][role].sign(gate.RECEIPT_DOMAIN + canonical(payload))
                    ),
                }
            )
        )
    else:
        (c["bundle"] / "rekor-entry.json").write_bytes(b"{}")
    code, result = run_control(c, capsys)
    assert code == result["exit_code"] == 2
    assert result["decision"] == result["status"] == "NOT_READY"
    assert expected in result["reason_codes"]
    assert result["refusals"] and result["production_authority_earned"] is False
    if mutation in ("signature", "control", "policy", "cache"):
        assert result["reason_codes"] == [expected]


def test_synthetic_root_is_not_accepted_by_production_pin(complete_gate_control, monkeypatch):
    c = complete_gate_control
    monkeypatch.setattr(
        external_anchor,
        "LOG_KEY_ID",
        "c0d23d6ad406973f9559f3ba2d1ca01f84147d8ffc5b8445c224f98b9591801d",
    )
    result = gate.check_evidence(
        c["bundle"],
        c["db"],
        policy_path=c["policy"],
        policy_sha256=digest(c["policy"].read_bytes()),
    )
    assert result["status"] == "NOT_READY"
    assert "ANCHOR_INVALID" in result["reason_codes"]
