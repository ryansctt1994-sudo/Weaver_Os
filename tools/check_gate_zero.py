"""Fail-closed repository governance self-check for Weaver OS Gate Zero."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "governance" / "gate-zero.json"


class GateZeroError(RuntimeError):
    pass


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        raise GateZeroError("POLICY_MISSING")
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateZeroError(f"POLICY_INVALID_JSON:{exc.msg}") from exc
    if not isinstance(data, dict):
        raise GateZeroError("POLICY_NOT_OBJECT")
    return data


def require_bool(mapping: dict, key: str) -> None:
    if mapping.get(key) is not True:
        raise GateZeroError(f"CONTROL_NOT_REQUIRED:{key}")


def main() -> int:
    policy = load_policy()

    if policy.get("schema_version") != "1.0":
        raise GateZeroError("SCHEMA_VERSION_UNSUPPORTED")
    if policy.get("policy_id") != "WEAVER-GATE-ZERO-1":
        raise GateZeroError("POLICY_ID_MISMATCH")
    if policy.get("repository") != "ryansctt1994-sudo/Weaver_Os":
        raise GateZeroError("REPOSITORY_MISMATCH")
    if policy.get("default_branch") != "main":
        raise GateZeroError("DEFAULT_BRANCH_MISMATCH")

    controls = policy.get("required_server_controls")
    if not isinstance(controls, dict):
        raise GateZeroError("SERVER_CONTROLS_MISSING")
    for key in (
        "pull_request_only",
        "block_force_pushes",
        "block_deletions",
        "require_linear_history",
        "require_status_checks",
    ):
        require_bool(controls, key)

    required_files = policy.get("required_repository_files")
    workflows = policy.get("required_workflow_files")
    if not isinstance(required_files, list) or not all(
        isinstance(item, str) for item in required_files
    ):
        raise GateZeroError("REQUIRED_FILES_INVALID")
    if not isinstance(workflows, list) or not all(isinstance(item, str) for item in workflows):
        raise GateZeroError("REQUIRED_WORKFLOWS_INVALID")

    missing = [rel for rel in required_files + workflows if not (ROOT / rel).is_file()]
    if missing:
        raise GateZeroError("MISSING_REQUIRED:" + ",".join(sorted(missing)))

    governance = policy.get("governance_coordinates")
    if governance != {
        "witness": "W0",
        "operational_authority": "O0_WITHHELD",
        "production": "PROHIBITED",
    }:
        raise GateZeroError("GOVERNANCE_COORDINATE_MISMATCH")

    print("GATE_ZERO_DECLARATION_PASS")
    print("SERVER_ENFORCEMENT_NOT_PROVEN")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateZeroError as exc:
        print(f"GATE_ZERO_DECLARATION_FAIL:{exc}")
        raise SystemExit(2) from exc
