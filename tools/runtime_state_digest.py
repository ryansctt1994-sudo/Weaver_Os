"""Bounded runtime-state observation and digest contract.

This module defines how a verifier may obtain state from an external runtime
without trusting a digest supplied by the manifest under test.

It verifies mechanics only. A successful observation is not independent
reproduction, witness qualification, authority, or production permission.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from tools.spine_hash import canonical, sha256_hex

_SCHEMA = "weaver-runtime-state-1"
_ALLOWED_BINDING_KINDS = {"git_commit": 40, "sha256": 64}
_REQUIRED_ENVELOPE_FIELDS = {
    "schema",
    "runtime_id",
    "source_binding",
    "replay_input_digest",
    "state",
}


class RuntimeStateError(ValueError):
    """Raised when runtime-state observation fails closed."""


@dataclass(frozen=True)
class RuntimeStateObservation:
    runtime_id: str
    source_binding_kind: str
    source_binding_value: str
    replay_input_digest: str
    state_digest: str
    command: tuple[str, ...]
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str


def state_digest(state: dict[str, Any]) -> str:
    """Return SHA-256 of canonical JSON for one runtime state object."""
    return sha256_hex(canonical(state))


def _valid_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(char in "0123456789abcdef" for char in value)
    )


def parse_runtime_envelope(raw_stdout: bytes) -> dict[str, Any]:
    """Parse one exact runtime-state envelope from stdout."""
    try:
        document = json.loads(raw_stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeStateError("RUNTIME_OUTPUT_INVALID_JSON") from exc

    if not isinstance(document, dict):
        raise RuntimeStateError("RUNTIME_OUTPUT_NOT_OBJECT")

    fields = set(document)
    missing = sorted(_REQUIRED_ENVELOPE_FIELDS - fields)
    if missing:
        raise RuntimeStateError("RUNTIME_OUTPUT_FIELDS_MISSING:" + ",".join(missing))

    extra = sorted(fields - _REQUIRED_ENVELOPE_FIELDS)
    if extra:
        raise RuntimeStateError("RUNTIME_OUTPUT_FIELDS_UNRECOGNIZED:" + ",".join(extra))

    if document.get("schema") != _SCHEMA:
        raise RuntimeStateError("RUNTIME_OUTPUT_SCHEMA_UNSUPPORTED")

    runtime_id = document.get("runtime_id")
    if not isinstance(runtime_id, str) or not runtime_id:
        raise RuntimeStateError("RUNTIME_ID_INVALID")

    binding = document.get("source_binding")
    if not isinstance(binding, dict) or set(binding) != {"kind", "value"}:
        raise RuntimeStateError("SOURCE_BINDING_INVALID")

    kind = binding.get("kind")
    value = binding.get("value")
    if not isinstance(kind, str) or kind not in _ALLOWED_BINDING_KINDS:
        raise RuntimeStateError("SOURCE_BINDING_KIND_UNSUPPORTED")
    if not _valid_hex(value, _ALLOWED_BINDING_KINDS[kind]):
        raise RuntimeStateError("SOURCE_BINDING_VALUE_INVALID")

    replay_input_digest = document.get("replay_input_digest")
    if not _valid_hex(replay_input_digest, 64):
        raise RuntimeStateError("REPLAY_INPUT_DIGEST_INVALID")

    state = document.get("state")
    if not isinstance(state, dict):
        raise RuntimeStateError("RUNTIME_STATE_NOT_OBJECT")

    return document


def observe_runtime_state(
    command: Sequence[str],
    *,
    expected_runtime_id: str,
    expected_binding_kind: str,
    expected_binding_value: str,
    expected_replay_input_digest: str,
    timeout_seconds: int = 30,
    max_stdout_bytes: int = 65_536,
    max_stderr_bytes: int = 65_536,
) -> RuntimeStateObservation:
    """Execute a runtime command and derive a state digest from its output.

    The command is executed without a shell. Source identity and replay-input
    identity are supplied independently by the caller and must match the
    runtime's envelope.
    """
    argv = tuple(command)
    if not argv or not all(isinstance(item, str) and item for item in argv):
        raise RuntimeStateError("RUNTIME_COMMAND_INVALID")
    if timeout_seconds <= 0:
        raise RuntimeStateError("RUNTIME_TIMEOUT_INVALID")
    if max_stdout_bytes <= 0 or max_stderr_bytes <= 0:
        raise RuntimeStateError("RUNTIME_OUTPUT_BOUND_INVALID")

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeStateError(f"RUNTIME_EXECUTION_FAILED:{type(exc).__name__}") from exc

    if len(result.stdout) > max_stdout_bytes:
        raise RuntimeStateError("RUNTIME_STDOUT_TOO_LARGE")
    if len(result.stderr) > max_stderr_bytes:
        raise RuntimeStateError("RUNTIME_STDERR_TOO_LARGE")
    if result.returncode != 0:
        raise RuntimeStateError(f"RUNTIME_EXIT_NONZERO:{result.returncode}")

    document = parse_runtime_envelope(result.stdout)
    binding = document["source_binding"]

    if document["runtime_id"] != expected_runtime_id:
        raise RuntimeStateError("RUNTIME_ID_MISMATCH")
    if binding["kind"] != expected_binding_kind:
        raise RuntimeStateError("SOURCE_BINDING_KIND_MISMATCH")
    if binding["value"] != expected_binding_value:
        raise RuntimeStateError("SOURCE_BINDING_VALUE_MISMATCH")
    if document["replay_input_digest"] != expected_replay_input_digest:
        raise RuntimeStateError("REPLAY_INPUT_DIGEST_MISMATCH")

    return RuntimeStateObservation(
        runtime_id=document["runtime_id"],
        source_binding_kind=binding["kind"],
        source_binding_value=binding["value"],
        replay_input_digest=document["replay_input_digest"],
        state_digest=state_digest(document["state"]),
        command=argv,
        exit_code=result.returncode,
        stdout_sha256=sha256_hex(result.stdout),
        stderr_sha256=sha256_hex(result.stderr),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-runtime-id", required=True)
    parser.add_argument(
        "--expected-binding-kind",
        required=True,
        choices=tuple(sorted(_ALLOWED_BINDING_KINDS)),
    )
    parser.add_argument("--expected-binding-value", required=True)
    parser.add_argument("--expected-replay-input-digest", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    try:
        observation = observe_runtime_state(
            command,
            expected_runtime_id=args.expected_runtime_id,
            expected_binding_kind=args.expected_binding_kind,
            expected_binding_value=args.expected_binding_value,
            expected_replay_input_digest=args.expected_replay_input_digest,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeStateError as exc:
        print(f"RUNTIME_STATE_REFUSED:{exc}", file=sys.stderr)
        return 2

    print(json.dumps(asdict(observation), sort_keys=True))
    print("EVIDENCE_CEILING: RUNTIME_STATE_CONTRACT_MECHANICS")
    print("AUTHORITY: O0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
