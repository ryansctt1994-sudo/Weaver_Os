#!/usr/bin/env python3
"""Fail closed on promotion-freeze invariant violations."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

AUTHORITY_CEILING = "O0"
SPEC_STATUSES = {"SPECIFICATION_CANDIDATE"}
GREEN_STATUSES = {"CI_QUALIFIED", "CI_QUALIFIED_CORRECTION"}
BLOCKED = {"BLOCKED_RED", "BLOCKED_ON_RC1", "BLOCKED_ON_RC2"}


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"FREEZE_INVARIANT_FAIL: {error}", file=sys.stderr)
    sys.exit(1)


def main(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("authority_ceiling") != AUTHORITY_CEILING:
        errors.append("portfolio authority ceiling is not O0")
    if data.get("production") != "prohibited":
        errors.append("production is not prohibited")

    objects = data.get("objects") or []
    by_id = {obj.get("id"): obj for obj in objects}
    if len(by_id) != len(objects):
        errors.append("object ids are not unique")

    for obj in objects:
        oid = obj.get("id", "<missing>")
        authority = obj.get("authority")
        status = obj.get("status")
        if authority != AUTHORITY_CEILING:
            errors.append(f"{oid}: authority {authority!r} is not {AUTHORITY_CEILING}")
        if status in GREEN_STATUSES and authority != AUTHORITY_CEILING:
            errors.append(f"{oid}: green checks raised authority")
        if obj.get("prohibited_claims") and "authority promotion" not in obj["prohibited_claims"] and status in BLOCKED:
            errors.append(f"{oid}: blocked object does not prohibit authority promotion")
        source = obj.get("source_head")
        merge = obj.get("verified_merge_sha") or obj.get("recorded_merge_ref")
        if source and merge and source == merge:
            errors.append(f"{oid}: source_sha and merge_sha collapsed")
        if source and merge and obj.get("verified_merge_sha_status", obj.get("recorded_merge_ref_status")) != "recorded-distinct-object":
            errors.append(f"{oid}: distinct merge object is not explicitly marked")
        if status in SPEC_STATUSES:
            if obj.get("draft") is not True:
                errors.append(f"{oid}: specification candidate is not draft")
            if obj.get("runtime_implemented") is not False:
                errors.append(f"{oid}: specification recorded as implemented runtime")
            if obj.get("missing_capability") != "NO_RUNTIME_PERSISTENCE_IMPLEMENTATION":
                errors.append(f"{oid}: missing persistence capability is not explicit")
        if status in BLOCKED and obj.get("promotion") is not False and obj.get("promotion") != "forbidden":
            errors.append(f"{oid}: blocked object is not promotion-forbidden")
        if status == "BLOCKED_ON_RC1" and obj.get("predecessor") != "wgrsi-rc1-pr-4":
            errors.append(f"{oid}: RC2 predecessor is not RC1")
        if status == "BLOCKED_ON_RC2" and obj.get("predecessor") != "wgrsi-rc2-pr-5":
            errors.append(f"{oid}: RC3 predecessor is not RC2")
        if status in BLOCKED and not obj.get("failing_jobs"):
            errors.append(f"{oid}: blocked object has no individual failing jobs")
        if oid == "introspection-twin-pr-1":
            record = obj.get("evidence_record") or {}
            if record.get("false_green_run") != 37189158459:
                errors.append("introspection false-green run is not preserved")
            if not record.get("corrected_runs"):
                errors.append("introspection corrected run is not preserved")

    required = {
        "weaver-activation-runtime-pr-65",
        "introspection-twin-pr-1",
        "weaver-recovery-pr-66",
        "wgrsi-rc1-pr-4",
        "wgrsi-rc2-pr-5",
        "wgrsi-rc3-pr-6",
    }
    missing = required - set(by_id)
    if missing:
        errors.append(f"missing required objects: {sorted(missing)}")
    if errors:
        fail(errors)
    print(f"FREEZE_OK {data.get('freeze_id')} objects={len(objects)}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "PORTFOLIO_PROMOTION_FREEZE.yaml"))
