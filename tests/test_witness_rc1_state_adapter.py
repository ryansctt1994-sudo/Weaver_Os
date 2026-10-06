from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.runtime_state_digest import observe_runtime_state, state_digest
from tools.spine_hash import canonical, sha256_hex
from tools.witness_rc1_state_adapter import (
    CORE_PATH,
    MANIFEST_PATH,
    RUNTIME_ID,
    build_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "tests" / "fixtures" / "witness_rc1_authorized_command.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_rc1_core_hash_matches_release_manifest():
    manifest = load_json(MANIFEST_PATH)
    expected = manifest["files"]["src/weaver_core.py"]
    assert sha256_hex(CORE_PATH.read_bytes()) == expected


def test_rc1_adapter_emits_contract_envelope():
    document = load_json(COMMAND)
    envelope = build_envelope(document)

    assert envelope["schema"] == "weaver-runtime-state-1"
    assert envelope["runtime_id"] == RUNTIME_ID
    assert envelope["source_binding"]["kind"] == "sha256"
    assert envelope["replay_input_digest"] == sha256_hex(canonical(document))
    assert envelope["state"]["protected"] == {"counter": 1}
    assert envelope["state"]["used_command_ids"] == ["C1"]
    assert envelope["state"]["last_verdict"] == "ACCEPT"


def test_contract_observer_accepts_real_rc1_adapter():
    document = load_json(COMMAND)
    manifest = load_json(MANIFEST_PATH)
    expected_core = manifest["files"]["src/weaver_core.py"]
    expected_input = sha256_hex(canonical(document))

    observation = observe_runtime_state(
        [sys.executable, "-m", "tools.witness_rc1_state_adapter", str(COMMAND)],
        expected_runtime_id=RUNTIME_ID,
        expected_binding_kind="sha256",
        expected_binding_value=expected_core,
        expected_replay_input_digest=expected_input,
    )

    envelope = build_envelope(document)
    assert observation.state_digest == state_digest(envelope["state"])


def test_full_state_digest_changes_when_command_changes():
    baseline = load_json(COMMAND)
    changed = json.loads(json.dumps(baseline))
    changed["cmd"]["command_id"] = "C2"
    changed["cmd"]["authorized"] = False

    baseline_state = build_envelope(baseline)["state"]
    changed_state = build_envelope(changed)["state"]

    assert state_digest(baseline_state) != state_digest(changed_state)
