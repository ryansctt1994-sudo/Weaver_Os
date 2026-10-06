from __future__ import annotations

import hashlib
import json
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


RUNTIME_TEMPLATE = r"""#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

RUNTIME_ID = "__RUNTIME_ID__"


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

__MUTATE_SNIPPET__

document = {
    "schema": "weaver-runtime-state-1",
    "runtime_id": RUNTIME_ID,
    "source_binding": {"kind": "sha256", "value": __BINDING_EXPR__},
    "replay_input_digest": __REPLAY_EXPR__,
    "state": projection,
}
print(json.dumps(document, sort_keys=True))
"""


def canonical_digest(data) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_runtime(
    root: Path,
    *,
    wrong_state: bool = False,
    runtime_id: str = "test-e35-runtime",
    wrong_binding: bool = False,
    wrong_replay: bool = False,
    mutate_self: bool = False,
    mutate_ledger: bool = False,
    executable: bool = True,
) -> tuple[Path, str]:
    path = root / "runtime.py"
    state_expr = '"WRONG"' if wrong_state else "state"
    binding_expr = '"0" * 64' if wrong_binding else "artifact_hash"
    replay_expr = '"0" * 64' if wrong_replay else "replay_digest"
    mutations = []
    if mutate_self:
        mutations.append(
            'Path(__file__).write_text(Path(__file__).read_text(encoding="utf-8") + '
            '"\\n# mutated during run\\n", encoding="utf-8")'
        )
    if mutate_ledger:
        mutations.append(
            'ledger_path.write_text(ledger_path.read_text(encoding="utf-8") + '
            '"\\n", encoding="utf-8")'
        )
    mutation_snippet = "\n".join(mutations) if mutations else "pass"

    content = (
        RUNTIME_TEMPLATE
        .replace("__RUNTIME_ID__", runtime_id)
        .replace("__STATE_EXPR__", state_expr)
        .replace("__BINDING_EXPR__", binding_expr)
        .replace("__REPLAY_EXPR__", replay_expr)
        .replace("__MUTATE_SNIPPET__", mutation_snippet)
    )
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def write_ledger(root: Path, *, name: str = "authority_ledger.json") -> Path:
    path = root / name
    path.write_text(json.dumps(LEDGER), encoding="utf-8")
    return path


def write_sut(
    root: Path,
    artifact_hash: str,
    ledger: Path,
    *,
    projection_method: str = "authority-transition-reducer-v1",
    ledger_file_sha256: str | None = None,
    replay_input_digest: str | None = None,
) -> Path:
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    path = evidence / "e35-runtime-sut.json"
    ledger_bytes = ledger.read_bytes()
    ledger_document = json.loads(ledger_bytes.decode("utf-8"))
    record = {
        "schema": "weaver-e35-runtime-sut-2",
        "status": "ADMITTED_CANDIDATE",
        "reason": None,
        "runtime_id": "test-e35-runtime",
        "artifact_path": "runtime.py",
        "artifact_sha256": artifact_hash,
        "ledger_path": ledger.name,
        "ledger_file_sha256": (
            ledger_file_sha256
            if ledger_file_sha256 is not None
            else hashlib.sha256(ledger_bytes).hexdigest()
        ),
        "replay_input_digest": (
            replay_input_digest
            if replay_input_digest is not None
            else canonical_digest(ledger_document)
        ),
        "projection_method": projection_method,
        "launch_mode": "DIRECT_ARTIFACT_EXEC",
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def assert_refused(exc, code: str):
    assert exc.value.code == code
    assert exc.value.exit_code == 1


def test_checked_in_runtime_sut_is_explicitly_unbound():
    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut()
    assert exc.value.code.startswith("E35_RUNTIME_SUT_UNBOUND:")
    assert exc.value.exit_code == 1


def test_gate_positive_control_qualifies_exact_direct_replay(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    artifact, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    receipt = qualify_e35_runtime(sut_path=sut)

    assert artifact.is_file()
    assert receipt.result == "LOCAL_CANDIDATE_REPLAY_PASS"
    assert receipt.runtime_state_digest == receipt.local_reference_state_digest
    assert receipt.local_reference_state == {
        "receipt_id": "T-1",
        "state": "EXECUTED",
    }
    assert receipt.execution_binding_class == "DIRECT_PATH_EXEC_PRE_POST_HASHED"
    assert receipt.atomic_process_identity == "NOT_ESTABLISHED"
    assert receipt.e35_admission == "WITHHELD"
    assert receipt.independent_reproduction == "NOT_ESTABLISHED"
    assert receipt.witness_state == "W0"
    assert receipt.authority == "O0_WITHHELD"
    assert receipt.production == "PROHIBITED"


def test_gate_rejects_runtime_state_projection_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, wrong_state=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert_refused(exc, "E35_RUNTIME_STATE_DIGEST_MISMATCH")


def test_gate_rejects_artifact_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, "0" * 64, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert_refused(exc, "E35_RUNTIME_ARTIFACT_HASH_MISMATCH")


def test_gate_requires_directly_executable_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, executable=False)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert_refused(exc, "E35_RUNTIME_ARTIFACT_NOT_EXECUTABLE")


def test_gate_rejects_descriptor_command_injection(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)
    record = json.loads(sut.read_text(encoding="utf-8"))
    record["command"] = ["python", "-c", "print('spoof')", "{artifact}", "{ledger}"]
    sut.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert exc.value.code == "E35_RUNTIME_SUT_FIELDS_UNRECOGNIZED:command"


def test_gate_rejects_non_equivalent_projection_method(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(
        tmp_path,
        artifact_hash,
        ledger,
        projection_method="some-richer-runtime-state-v1",
    )

    with pytest.raises(E35RuntimeGateError) as exc:
        load_runtime_sut(sut)

    assert exc.value.code == "E35_RUNTIME_PROJECTION_NOT_REFERENCE_EQUIVALENT"


def test_gate_rejects_semantically_same_but_byte_changed_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)
    ledger.write_text(ledger.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert_refused(exc, "E35_LEDGER_FILE_HASH_MISMATCH")


def test_gate_rejects_wrong_pinned_semantic_digest(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    sut = write_sut(
        tmp_path,
        artifact_hash,
        ledger,
        replay_input_digest="0" * 64,
    )

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert_refused(exc, "E35_REPLAY_INPUT_DIGEST_MISMATCH")


def test_gate_rejects_unadmitted_ledger_path(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path)
    ledger = write_ledger(tmp_path)
    alternate = write_ledger(tmp_path, name="alternate.json")
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut, ledger_path=alternate)

    assert_refused(exc, "E35_LEDGER_PATH_NOT_ADMITTED")


def test_gate_rejects_runtime_id_substitution(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, runtime_id="other-runtime")
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert exc.value.code.endswith("RUNTIME_ID_MISMATCH")


def test_gate_rejects_runtime_source_binding_substitution(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, wrong_binding=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert exc.value.code.endswith("SOURCE_BINDING_VALUE_MISMATCH")


def test_gate_rejects_runtime_replay_digest_substitution(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, wrong_replay=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert exc.value.code.endswith("REPLAY_INPUT_DIGEST_MISMATCH")


def test_gate_rejects_artifact_mutated_during_execution(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, mutate_self=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert_refused(exc, "E35_RUNTIME_ARTIFACT_CHANGED_DURING_RUN")


def test_gate_rejects_ledger_mutated_during_execution(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.e35_runtime_gate.ROOT", tmp_path)
    _, artifact_hash = write_runtime(tmp_path, mutate_ledger=True)
    ledger = write_ledger(tmp_path)
    sut = write_sut(tmp_path, artifact_hash, ledger)

    with pytest.raises(E35RuntimeGateError) as exc:
        qualify_e35_runtime(sut_path=sut)

    assert_refused(exc, "E35_REPLAY_INPUT_CHANGED_DURING_RUN")
