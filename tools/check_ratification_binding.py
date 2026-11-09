"""Check crosswalk-to-decision consistency, without conferring ratification.

This is a structural consistency check of committed text, not verification of
steward identity, consent, signatures, branch protection, or independent review.
It deliberately accepts only the presently defined W0 and O0 axes; adding a
higher rung requires changing this checker and reviewing the new governance rule.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from tools.check_evidence_crosswalk import ROOT
from tools.check_evidence_crosswalk import check as check_crosswalk

ID_RE = re.compile(r"GD-[0-9]{4}\Z")


def _field(text: str, name: str) -> str | None:
    match = re.search(
        r"^- \*\*" + re.escape(name) + r":\*\*\s*(.+?)\s*$", text, re.MULTILINE
    )
    return match.group(1).strip() if match else None


def check_binding(doc: Any, decision_text: str | None) -> list[str]:
    """Validate crosswalk axis boundaries and decision text against metadata."""
    if not isinstance(doc, dict):
        return ["crosswalk must be a JSON object"]
    errors: list[str] = []
    axes = doc.get("orthogonal_axes")
    if not isinstance(axes, list) or len(axes) != 2:
        errors.append("orthogonal_axes must contain exactly W and O")
    else:
        ids = [axis.get("id") if isinstance(axis, dict) else None for axis in axes]
        if set(ids) != {"W", "O"} or len(set(ids)) != 2:
            errors.append("orthogonal_axes must contain unique W and O axes")
        else:
            for axis in axes:
                expected = axis["id"] + "0"
                levels = axis.get("defined_levels")
                if (
                    not isinstance(levels, list)
                    or len(levels) != 1
                    or not isinstance(levels[0], dict)
                    or levels[0].get("level") != expected
                ):
                    errors.append(
                        f"{axis['id']}: only {expected} is currently defined (GD-0001 D2)"
                    )

    if doc.get("status") != "RATIFIED":
        return errors
    rat = doc.get("ratification")
    if not isinstance(rat, dict):
        return errors + ["RATIFIED requires ratification metadata"]
    decision_id = rat.get("decision_id")
    if not isinstance(decision_id, str) or not ID_RE.fullmatch(decision_id):
        return errors + ["ratification decision_id must match GD-NNNN"]
    if decision_text is None:
        return errors + [f"referenced decision {decision_id} missing or unreadable"]

    for key, expected in (
        ("Decision ID", decision_id),
        ("Date", rat.get("ratified_at")),
        ("Mode", rat.get("mode")),
    ):
        actual = _field(decision_text, key)
        if not isinstance(expected, str) or actual != expected:
            errors.append(f"decision {key} does not match crosswalk metadata")

    stewards = rat.get("ratified_by")
    recorded = _field(decision_text, "Ratified by")
    if not isinstance(stewards, list) or not stewards or not isinstance(recorded, str):
        errors.append("decision Ratified by signatory line missing or invalid")
    else:
        for steward in stewards:
            if not isinstance(steward, str) or not steward:
                errors.append("ratification steward identifier missing")
                continue
            pattern = rf"(?<![A-Za-z0-9_-])@?{re.escape(steward)}(?![A-Za-z0-9_-])"
            if not re.search(pattern, recorded):
                errors.append(f"decision Ratified by does not name steward {steward}")
    if rat.get("mode") == "SINGLE_STEWARD" and "C-DUAL-001" not in decision_text:
        errors.append("single-steward decision must acknowledge C-DUAL-001")
    return errors


def check_repository(root: Path = ROOT) -> list[str]:
    try:
        doc = json.loads((root / "governance/evidence_crosswalk.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read crosswalk: {exc}"]
    errors = check_crosswalk(doc)
    if not isinstance(doc, dict):
        return errors
    decision_text = None
    rat = doc.get("ratification")
    decision_id = rat.get("decision_id") if isinstance(rat, dict) else None
    if (
        doc.get("status") == "RATIFIED"
        and isinstance(decision_id, str)
        and ID_RE.fullmatch(decision_id)
    ):
        path = root / "governance" / "decisions" / f"{decision_id}.md"
        try:
            decision_text = path.read_text(encoding="utf-8")
        except OSError:
            pass
    return errors + check_binding(doc, decision_text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)
    errors = check_repository(args.root)
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print(
        "OK: ratification text and W/O axis declarations consistent; "
        "independent approval NOT verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
