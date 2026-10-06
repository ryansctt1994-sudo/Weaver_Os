"""Adapter from the frozen Weaver witness RC1 runtime to the runtime-state contract.

Scope is intentionally narrow: one command document is replayed through the
frozen RC1 Runtime implementation. The adapter emits the full in-memory
behavior-relevant state after execution.

This is not the E3.5 authority-ledger runtime and must not be cited as E3.5.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from tools.spine_hash import canonical, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "releases" / "weaver-witness-signed-rc1"
CORE_PATH = RELEASE_ROOT / "src" / "weaver_core.py"
MANIFEST_PATH = RELEASE_ROOT / "MANIFEST.json"
SCHEMA = "weaver-runtime-state-1"
RUNTIME_ID = "weaver-witness-signed-rc1"


class WitnessRC1AdapterError(ValueError):
    """Raised when the bounded RC1 adapter cannot produce a valid state envelope."""


def _load_core() -> ModuleType:
    spec = importlib.util.spec_from_file_location("weaver_witness_rc1_core", CORE_PATH)
    if spec is None or spec.loader is None:
        raise WitnessRC1AdapterError("CORE_IMPORT_SPEC_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise WitnessRC1AdapterError(f"MISSING_INPUT:{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WitnessRC1AdapterError("INPUT_INVALID_JSON") from exc


def _core_source_hash() -> str:
    if not CORE_PATH.is_file():
        raise WitnessRC1AdapterError("CORE_SOURCE_MISSING")
    return sha256_hex(CORE_PATH.read_bytes())


def _manifest_core_hash() -> str:
    manifest = _load_json(MANIFEST_PATH)
    if not isinstance(manifest, dict):
        raise WitnessRC1AdapterError("RELEASE_MANIFEST_NOT_OBJECT")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise WitnessRC1AdapterError("RELEASE_MANIFEST_FILES_INVALID")
    value = files.get("src/weaver_core.py")
    if not isinstance(value, str):
        raise WitnessRC1AdapterError("RELEASE_MANIFEST_CORE_HASH_MISSING")
    return value


def build_envelope(command_document: Any) -> dict[str, Any]:
    """Replay one command and emit a contract-compatible state envelope."""
    if not isinstance(command_document, dict) or set(command_document) != {"cmd"}:
        raise WitnessRC1AdapterError("COMMAND_DOCUMENT_INVALID")

    raw_command = command_document.get("cmd")
    if not isinstance(raw_command, dict):
        raise WitnessRC1AdapterError("COMMAND_PAYLOAD_INVALID")

    computed_core_hash = _core_source_hash()
    if computed_core_hash != _manifest_core_hash():
        raise WitnessRC1AdapterError("CORE_SOURCE_MANIFEST_MISMATCH")

    core = _load_core()
    command_type = getattr(core, "Command", None)
    runtime_type = getattr(core, "Runtime", None)
    if command_type is None or runtime_type is None:
        raise WitnessRC1AdapterError("CORE_RUNTIME_SYMBOLS_MISSING")

    try:
        command = command_type(**raw_command)
        runtime = runtime_type(command.experiment_id)
        verdict, receipt = runtime.execute(command)
    except Exception as exc:
        raise WitnessRC1AdapterError(f"RUNTIME_REPLAY_FAILED:{type(exc).__name__}") from exc

    protected = getattr(runtime, "protected", None)
    used = getattr(runtime, "used", None)
    chronicle = getattr(runtime, "chronicle", None)
    entries = getattr(chronicle, "entries", None)

    if not isinstance(protected, dict):
        raise WitnessRC1AdapterError("PROTECTED_STATE_INVALID")
    if not isinstance(used, set):
        raise WitnessRC1AdapterError("REPLAY_CACHE_STATE_INVALID")
    if not isinstance(entries, list):
        raise WitnessRC1AdapterError("CHRONICLE_STATE_INVALID")
    if not isinstance(verdict, str) or not isinstance(receipt, dict):
        raise WitnessRC1AdapterError("RUNTIME_RESULT_INVALID")

    state = {
        "protected": protected,
        "used_command_ids": sorted(str(item) for item in used),
        "chronicle_entries": entries,
        "last_verdict": verdict,
        "last_receipt": receipt,
    }

    return {
        "schema": SCHEMA,
        "runtime_id": RUNTIME_ID,
        "source_binding": {
            "kind": "sha256",
            "value": computed_core_hash,
        },
        "replay_input_digest": sha256_hex(canonical(command_document)),
        "state": state,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command_document", type=Path)
    args = parser.parse_args(argv)

    try:
        envelope = build_envelope(_load_json(args.command_document))
    except WitnessRC1AdapterError as exc:
        print(f"WITNESS_RC1_STATE_REFUSED:{exc}", file=sys.stderr)
        return 2

    print(json.dumps(envelope, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
