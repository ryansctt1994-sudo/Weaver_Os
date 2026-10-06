from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from tools.e35_runtime_gate import (
    E35RuntimeGateError,
    load_runtime_sut,
    qualify_e35_runtime,
)

LEDGER = [
    {
        "sequence_number": 1,
        "event_type": "STATE_TRANSITION",
        "payload": (
            '{"current_state":"DRAFT","receipt_id":"T-1",'
            '"target_state":"EVIDENCED"}'
        ),
    },
    {
        "sequence_number": 2,
        "event_type": "STATE_TRANSITION",
        "payload": (
            '{"current_state":"EVIDENCED","receipt_id":"T-1",'
            '"target_state":"EXECUTED"}'
        ),
    },
]


RUNTIME_TEMPLATE = r"""
import hashlib
import json
import sys
from pathlib import Path

RUNTIME_ID = "test-e35-runtime"


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


ledger_path = Path(sys.argv[1])
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

receipt_id = None
state = None
for event in sorted(ledger, key=lambda item: item["sequence_number"]):
    payload = json.loads(event["payload"])
    if receipt_id is None:
        receipt_id = payload["receipt_id"]
        state = payload["current_state"]
    if payload["receipt_id"] != receipt_id:
        raise SystemExit(4)
    if payload["current_state"] != state:
        raise SystemExit(5)
    state = payload["target_state"]

projection = {"receipt_id": receipt_id, "state": __STATE_EXPR__}
artifact_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
replay_digest = hashlib.sha256(canonical(ledger)).hexdigest()

document = {
    "schema": "weaver-runtime-state-1",
    "runtime_id": RUNTIME_ID,
    "source_binding": {"kind": "sha256", "value": artifact_hash},
    "replay_input_digest": replay_digest,
    "state": projection,
}
print(json.dumps(document, sort_keys=True))
"""


def write_runtime(root: Path, *, wrong_state: bool = False) -> tuple[Path, str]:
    path = root / "runtime.py"
    state_expr = '"WRONG"' if wrong_state else "state"
    path.write_text(
        RUNTIME_TEMPLATE.replace("__STATE_EXPR__", state_expr),
        encoding="utf-8",
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def write_ledger(root: Path) -> Path:
    path = root / "authority_ledger.json"
    path.write_text(json.dumps(LEDGER), encoding="utf-8")
    return path


def write_sut(root: Path, artifact_hash: str, *, projection_method=None) -> Path:
    evidence = root / "evidence"
    evidence.mkdir()
    path = evidence / "e35-runtime-sut.json"
    path.write_text(
        json.dumps(
            {
                "schema": "weaver-e35-runtime-sut-1",
                "status": "ADMITTED_CANDIDATE",
                "reason": None,
                "runtime_id": "test-e35-runtime",
                "artifact_path": "runtime.py",
                "artifact_sha256": artifact_hash,
                "projection_method": (
                    projection_method
                    if projection_method is not None
                    else "authority-transition-reducer-v1"
                ),
                "command": [sys.executable, "{artifact}", "{ledger}"],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_checked_in_runtime_sut_is_explicitly_unbound():
    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut()
    assert exc.value.code.startswith("E35_RUNTIME_SUT_UNBOUND:")
    assert exc.value.exit_code == 1


def test_gate_qualifies_equivalent_runtime_projection(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    artifact, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash)

    receipt = qualify_e35_runtime(sut_path=sut, ledger_path=ledger)

    assert artifact.is_file()
    assert receipt.result == "LOCAL_RUNTIME_REPLAY_PASS"
    assert receipt.runtime_state_digest == receipt.local_reference_state_digest
    assert receipt.local_reference_state == {
        "receipt_id": "T-1",
        "state": "EXECUTED",
    }
    assert receipt.execution_binding_class == "PRE_POST_HASHED_PATH_EXEC"
    assert receipt.operator_independence == "NOT_ESTABLISHED"
    assert receipt.witness_state == "W0"
    assert receipt.authority == "O0_WITHHELD"
    assert receipt.production == "PROHIBITED"


def test_gate_rejects_runtime_state_projection_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, wrong_state=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut, ledger_path=ledger)

    assert exc.value.code == "E35_RUNTIME_STATE_DIGEST_MISMATCH"
    assert exc.value.exit_code == 1


def test_gate_rejects_artifact_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    write_runtime(tmp_path)
    write_ledger(tmp_path)
    sut = write_sut(tmp_path, "0" * 64)

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert exc.value.code == "E35_RUNTIME_ARTIFACT_HASH_MISMATCH"
    assert exc.value.exit_code == 1


def test_gate_rejects_non_equivalent_projection_method(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    write_ledger(tmp_path)
    sut = write_sut(
        tmp_path,
        artifact_hash,
        projection_method="some-richer-runtime-state-v1",
    )

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert exc.value.code == "E35_RUNTIME_PROJECTION_NOT_REFERENCE_EQUIVALENT"
