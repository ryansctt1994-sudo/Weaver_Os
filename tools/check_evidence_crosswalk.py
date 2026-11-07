"""Fail-closed structural check for governance/evidence_crosswalk.json.

The checker validates shape and internal consistency only. It never ratifies
the crosswalk and never changes its status. Whether a mapping is *right* is a
steward decision recorded in the file's ``ratification`` block.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "governance" / "evidence_crosswalk.json"

TARGET_LEVELS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
STATUS_FLAG = "STATUS_FLAG"
EQUIVALENCES = {"exact", "floor", "partial", "none"}
STATUSES = {"PROPOSED", "RATIFIED"}
MIN_RATIFYING_STEWARDS = 2
RATIFICATION_MODES = {"DUAL_STEWARD", "SINGLE_STEWARD"}
# A single-steward ratification is legal only while it names the open blocker.
SINGLE_STEWARD_BLOCKER = "C-DUAL-001"


def _is_placeholder(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or value.strip().upper() in {
        "TBD",
        "TODO",
        "PENDING",
        "PLACEHOLDER",
    }


def check(doc: Any) -> list[str]:
    """Return a list of violations. An empty list means structurally valid."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["document must be a JSON object"]

    status = doc.get("status")
    if status not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}, got {status!r}")

    ratification = doc.get("ratification")
    if not isinstance(ratification, dict):
        errors.append("ratification block missing")
        ratification = {}
    if status == "RATIFIED":
        if _is_placeholder(ratification.get("decision_id")):
            errors.append("RATIFIED requires a non-placeholder decision_id")
        if _is_placeholder(ratification.get("ratified_at")):
            errors.append("RATIFIED requires ratified_at")
        mode = ratification.get("mode")
        stewards = ratification.get("ratified_by")
        if mode not in RATIFICATION_MODES:
            errors.append(f"RATIFIED requires mode in {sorted(RATIFICATION_MODES)}")
        elif not isinstance(stewards, list) or any(_is_placeholder(s) for s in stewards):
            errors.append("ratified_by must be a list of steward identifiers")
        elif mode == "DUAL_STEWARD" and len(set(stewards)) < MIN_RATIFYING_STEWARDS:
            errors.append(
                f"DUAL_STEWARD requires at least {MIN_RATIFYING_STEWARDS} distinct stewards"
            )
        elif mode == "SINGLE_STEWARD":
            if len(stewards) != 1:
                errors.append("SINGLE_STEWARD requires exactly one steward")
            limitation = ratification.get("limitation")
            if not isinstance(limitation, str) or SINGLE_STEWARD_BLOCKER not in limitation:
                errors.append(
                    f"SINGLE_STEWARD requires a limitation naming {SINGLE_STEWARD_BLOCKER}"
                )
    elif status == "PROPOSED" and (
        ratification.get("decision_id") or ratification.get("ratified_by")
    ):
        errors.append("PROPOSED crosswalk must not carry ratification data")

    levels = doc.get("target_ladder", {}).get("levels")
    if not isinstance(levels, list):
        errors.append("target_ladder.levels missing")
        levels = []
    names = [entry.get("level") for entry in levels if isinstance(entry, dict)]
    if tuple(names) != TARGET_LEVELS:
        errors.append(f"target ladder must be exactly {list(TARGET_LEVELS)} in order")
    for entry in levels:
        if isinstance(entry, dict) and _is_placeholder(entry.get("proof_obligation")):
            errors.append(f"{entry.get('level')}: proof_obligation missing")

    order = {level: i for i, level in enumerate(TARGET_LEVELS)}
    ladders = doc.get("source_ladders")
    if not isinstance(ladders, list) or not ladders:
        errors.append("source_ladders missing")
        ladders = []
    seen_ladders: set[str] = set()
    for ladder in ladders:
        ladder_id = ladder.get("id") if isinstance(ladder, dict) else None
        if not isinstance(ladder_id, str) or ladder_id in seen_ladders:
            errors.append(f"source ladder id missing or duplicated: {ladder_id!r}")
            continue
        seen_ladders.add(ladder_id)
        labels: set[str] = set()
        previous = -1
        for mapping in ladder.get("mappings", []):
            label = mapping.get("label")
            where = f"{ladder_id}:{label}"
            if label in labels:
                errors.append(f"{where}: duplicate label")
            labels.add(label)
            target = mapping.get("maps_to")
            equivalence = mapping.get("equivalence")
            if equivalence not in EQUIVALENCES:
                errors.append(f"{where}: equivalence must be one of {sorted(EQUIVALENCES)}")
            if target == STATUS_FLAG:
                if equivalence != "none":
                    errors.append(f"{where}: STATUS_FLAG mappings must use equivalence 'none'")
                continue
            if target not in order:
                errors.append(f"{where}: maps_to {target!r} is not an R level")
                continue
            if equivalence == "none":
                errors.append(f"{where}: an R-level mapping cannot have equivalence 'none'")
            if equivalence in {"floor", "partial"} and _is_placeholder(
                mapping.get("condition_for_higher")
            ):
                errors.append(f"{where}: {equivalence} mapping needs condition_for_higher")
            if order[target] < previous:
                errors.append(f"{where}: mapping is not monotonic within its ladder")
            previous = max(previous, order[target])
            if order[target] >= order["R6"]:
                errors.append(f"{where}: no legacy label may map to production authorization")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load crosswalk: {exc}")
        return 1
    errors = check(doc)
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print(f"OK: crosswalk structurally valid; status={doc['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
