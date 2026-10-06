"""Fail-closed admission gate for the E3.5 governance runtime.

This module does not provide a governance runtime. It qualifies a separately
admitted runtime artifact against an exact authority-ledger byte sequence and
the existing runtime-state observation contract.

A pass establishes bounded local candidate replay only. It does not establish
E3.5 admission, independent reproduction, witness status, authority, or
production permission.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from tools.authority_state import AuthorityStateError, replay_authority_state
from tools.runtime_state_digest import RuntimeStateError, observe_runtime_state
from tools.spine_hash import canonical, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUT_PATH = ROOT / "evidence" / "e35-runtime-sut.json"

SUT_SCHEMA = "weaver-e35-runtime-sut-2"
RECEIPT_SCHEMA = "weaver-e35-runtime-qualification-2"
REFERENCE_PROJECTION_METHOD = "authority-transition-reducer-v1"
DIRECT_LAUNCH_MODE = "DIRECT_ARTIFACT_EXEC"


class E35RuntimeGateError(ValueError):
    """Raised when E3.5 runtime admission or replay fails closed."""

    def __init__(self, code: str, *, exit_code: int = 2):
        self.code = code
        self.exit_code = exit_code
        super().__init__(code)


@dataclass(frozen=True)
class RuntimeSUT:
    runtime_id: str
    artifact_path: Path
    artifact_sha256: str
    ledger_path: Path
    ledger_file_sha256: str
    replay_input_digest: str
    projection_method: str
    launch_mode: str
    sut_record_sha256: str


@dataclass(frozen=True)
class E35RuntimeReceipt:
    schema: str
    result: str
    runtime_id: str
    sut_record_sha256: str
    artifact_sha256: str
    ledger_file_sha256: str
    replay_input_digest: str
    projection_method: str
    runtime_state_digest: str
    local_reference_state_digest: str
    local_reference_state: dict[str, str]
    events: int
    runtime_exit_code: int
    runtime_stdout_sha256: str
    runtime_stderr_sha256: str
    execution_binding_class: str
    atomic_process_identity: str
    e35_admission: str
    independent_reproduction: str
    witness_state: str
    authority: str
    production: str
    evidence_ceiling: str


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise E35RuntimeGateError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise E35RuntimeGateError(f"INVALID_JSON_CONSTANT:{value}")


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise E35RuntimeGateError(f"MISSING_ARTIFACT:{path.name}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise E35RuntimeGateError(f"INVALID_JSON:{path.name}") from exc


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _resolve_repo_relative(raw: Any, *, field: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise E35RuntimeGateError(f"{field}_INVALID")
    candidate = Path(raw)
    if candidate.is_absolute():
        raise E35RuntimeGateError(f"{field}_MUST_BE_RELATIVE")
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise E35RuntimeGateError(f"{field}_ESCAPES_REPOSITORY") from exc
    return resolved


def load_runtime_sut(path: Path = DEFAULT_SUT_PATH) -> RuntimeSUT:
    """Load one explicitly admitted E3.5 runtime SUT description.

    The checked-in default is intentionally UNBOUND until a real governance
    runtime artifact and exact replay ledger are named and pinned.
    """
    raw_bytes = path.read_bytes() if path.is_file() else b""
    raw = _load_json(path)
    if not isinstance(raw, dict):
        raise E35RuntimeGateError("E35_RUNTIME_SUT_NOT_OBJECT")

    allowed = {
        "schema",
        "status",
        "reason",
        "runtime_id",
        "artifact_path",
        "artifact_sha256",
        "ledger_path",
        "ledger_file_sha256",
        "replay_input_digest",
        "projection_method",
        "launch_mode",
    }
    extra = sorted(set(raw) - allowed)
    if extra:
        raise E35RuntimeGateError(
            "E35_RUNTIME_SUT_FIELDS_UNRECOGNIZED:" + ",".join(extra)
        )

    if raw.get("schema") != SUT_SCHEMA:
        raise E35RuntimeGateError("E35_RUNTIME_SUT_SCHEMA_UNSUPPORTED")

    status = raw.get("status")
    if status == "UNBOUND":
        reason = raw.get("reason")
        if not isinstance(reason, str) or not reason:
            reason = "NO_ADMITTED_GOVERNANCE_RUNTIME"
        raise E35RuntimeGateError(
            f"E35_RUNTIME_SUT_UNBOUND:{reason}",
            exit_code=1,
        )
    if status != "ADMITTED_CANDIDATE":
        raise E35RuntimeGateError("E35_RUNTIME_SUT_STATUS_INVALID")

    runtime_id = raw.get("runtime_id")
    artifact_sha256 = raw.get("artifact_sha256")
    ledger_file_sha256 = raw.get("ledger_file_sha256")
    replay_input_digest = raw.get("replay_input_digest")
    projection_method = raw.get("projection_method")
    launch_mode = raw.get("launch_mode")

    if not isinstance(runtime_id, str) or not runtime_id:
        raise E35RuntimeGateError("E35_RUNTIME_ID_INVALID")
    if not _valid_sha256(artifact_sha256):
        raise E35RuntimeGateError("E35_RUNTIME_ARTIFACT_SHA256_INVALID")
    if not _valid_sha256(ledger_file_sha256):
        raise E35RuntimeGateError("E35_LEDGER_FILE_SHA256_INVALID")
    if not _valid_sha256(replay_input_digest):
        raise E35RuntimeGateError("E35_REPLAY_INPUT_DIGEST_INVALID")
    if projection_method != REFERENCE_PROJECTION_METHOD:
        raise E35RuntimeGateError("E35_RUNTIME_PROJECTION_NOT_REFERENCE_EQUIVALENT")
    if launch_mode != DIRECT_LAUNCH_MODE:
        raise E35RuntimeGateError("E35_RUNTIME_LAUNCH_MODE_UNSUPPORTED")

    artifact_path = _resolve_repo_relative(
        raw.get("artifact_path"), field="E35_RUNTIME_ARTIFACT_PATH"
    )
    ledger_path = _resolve_repo_relative(
        raw.get("ledger_path"), field="E35_LEDGER_PATH"
    )

    if not artifact_path.is_file():
        raise E35RuntimeGateError("E35_RUNTIME_ARTIFACT_MISSING", exit_code=1)
    if not os.access(artifact_path, os.X_OK):
        raise E35RuntimeGateError(
            "E35_RUNTIME_ARTIFACT_NOT_EXECUTABLE",
            exit_code=1,
        )
    if not ledger_path.is_file():
        raise E35RuntimeGateError("E35_LEDGER_MISSING", exit_code=1)

    actual_artifact_sha256 = sha256_hex(artifact_path.read_bytes())
    if actual_artifact_sha256 != artifact_sha256:
        raise E35RuntimeGateError(
            "E35_RUNTIME_ARTIFACT_HASH_MISMATCH",
            exit_code=1,
        )

    return RuntimeSUT(
        runtime_id=runtime_id,
        artifact_path=artifact_path,
        artifact_sha256=actual_artifact_sha256,
        ledger_path=ledger_path,
        ledger_file_sha256=ledger_file_sha256,
        replay_input_digest=replay_input_digest,
        projection_method=projection_method,
        launch_mode=launch_mode,
        sut_record_sha256=sha256_hex(raw_bytes),
    )


def _resolve_command(sut: RuntimeSUT) -> tuple[str, ...]:
    # The admitted artifact itself is argv[0]. A descriptor cannot substitute
    # an interpreter or wrapper that merely mentions the pinned artifact.
    return (str(sut.artifact_path), str(sut.ledger_path))


def qualify_e35_runtime(
    *,
    sut_path: Path = DEFAULT_SUT_PATH,
    ledger_path: Path | None = None,
) -> E35RuntimeReceipt:
    """Replay one exactly pinned authority ledger through one admitted artifact."""
    sut = load_runtime_sut(sut_path)

    if ledger_path is not None and ledger_path.resolve() != sut.ledger_path:
        raise E35RuntimeGateError("E35_LEDGER_PATH_NOT_ADMITTED", exit_code=1)

    admitted_ledger_path = sut.ledger_path
    pre_ledger_bytes = admitted_ledger_path.read_bytes()
    pre_ledger_file_sha256 = sha256_hex(pre_ledger_bytes)
    if pre_ledger_file_sha256 != sut.ledger_file_sha256:
        raise E35RuntimeGateError("E35_LEDGER_FILE_HASH_MISMATCH", exit_code=1)

    ledger = _load_json(admitted_ledger_path)
    replay_input_digest = sha256_hex(canonical(ledger))
    if replay_input_digest != sut.replay_input_digest:
        raise E35RuntimeGateError("E35_REPLAY_INPUT_DIGEST_MISMATCH", exit_code=1)

    try:
        local_reference = replay_authority_state(ledger)
    except AuthorityStateError as exc:
        raise E35RuntimeGateError(
            f"E35_LEDGER_REFERENCE_INVALID:{exc}"
        ) from exc

    command = _resolve_command(sut)

    try:
        observation = observe_runtime_state(
            command,
            expected_runtime_id=sut.runtime_id,
            expected_binding_kind="sha256",
            expected_binding_value=sut.artifact_sha256,
            expected_replay_input_digest=replay_input_digest,
        )
    except RuntimeStateError as exc:
        raise E35RuntimeGateError(
            f"E35_RUNTIME_OBSERVATION_REFUSED:{exc}",
            exit_code=1,
        ) from exc

    post_artifact_sha256 = sha256_hex(sut.artifact_path.read_bytes())
    if post_artifact_sha256 != sut.artifact_sha256:
        raise E35RuntimeGateError(
            "E35_RUNTIME_ARTIFACT_CHANGED_DURING_RUN",
            exit_code=1,
        )

    post_ledger_bytes = admitted_ledger_path.read_bytes()
    post_ledger_file_sha256 = sha256_hex(post_ledger_bytes)
    if post_ledger_file_sha256 != sut.ledger_file_sha256:
        raise E35RuntimeGateError(
            "E35_REPLAY_INPUT_CHANGED_DURING_RUN",
            exit_code=1,
        )

    post_ledger = _load_json(admitted_ledger_path)
    post_replay_input_digest = sha256_hex(canonical(post_ledger))
    if post_replay_input_digest != replay_input_digest:
        raise E35RuntimeGateError(
            "E35_REPLAY_SEMANTICS_CHANGED_DURING_RUN",
            exit_code=1,
        )

    if observation.state_digest != local_reference.digest:
        raise E35RuntimeGateError(
            "E35_RUNTIME_STATE_DIGEST_MISMATCH",
            exit_code=1,
        )

    return E35RuntimeReceipt(
        schema=RECEIPT_SCHEMA,
        result="LOCAL_CANDIDATE_REPLAY_PASS",
        runtime_id=sut.runtime_id,
        sut_record_sha256=sut.sut_record_sha256,
        artifact_sha256=sut.artifact_sha256,
        ledger_file_sha256=sut.ledger_file_sha256,
        replay_input_digest=replay_input_digest,
        projection_method=sut.projection_method,
        runtime_state_digest=observation.state_digest,
        local_reference_state_digest=local_reference.digest,
        local_reference_state=dict(local_reference.state),
        events=local_reference.events,
        runtime_exit_code=observation.exit_code,
        runtime_stdout_sha256=observation.stdout_sha256,
        runtime_stderr_sha256=observation.stderr_sha256,
        execution_binding_class="DIRECT_PATH_EXEC_PRE_POST_HASHED",
        atomic_process_identity="NOT_ESTABLISHED",
        e35_admission="WITHHELD",
        independent_reproduction="NOT_ESTABLISHED",
        witness_state="W0",
        authority="O0_WITHHELD",
        production="PROHIBITED",
        evidence_ceiling="LOCAL_CANDIDATE_REPLAY",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sut", type=Path, default=DEFAULT_SUT_PATH)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="Optional assertion only; must resolve to the ledger pinned by the SUT record.",
    )
    args = parser.parse_args(argv)

    try:
        receipt = qualify_e35_runtime(
            sut_path=args.sut,
            ledger_path=args.ledger,
        )
    except E35RuntimeGateError as exc:
        print(f"E3.5_RUNTIME_WITHHELD:{exc.code}", file=sys.stderr)
        print("E35_ADMISSION: WITHHELD")
        print("WITNESS: W0")
        print("AUTHORITY: O0_WITHHELD")
        print("PRODUCTION: PROHIBITED")
        return exc.exit_code

    print(json.dumps(asdict(receipt), sort_keys=True))
    print("RESULT: E35_GATE_LOCAL_CANDIDATE_REPLAY_PASS")
    print("E35_ADMISSION: WITHHELD")
    print("INDEPENDENT_REPRODUCTION: NOT_ESTABLISHED")
    print("WITNESS: W0")
    print("AUTHORITY: O0_WITHHELD")
    print("PRODUCTION: PROHIBITED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
