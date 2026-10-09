"""Refuse to freeze a witness policy while declared versions disagree.

This module records the conflict. It does not select a governing version,
promote E3.5 or E4, or create a witness.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

FREEZE_STATUS = "DISCREPANCY_UNADJUDICATED"
AUTHORITY = "E2 | W0 | O0 WITHHELD | PRODUCTION PROHIBITED"

DECLARED_POLICIES = (
    {
        "identity": "e35-reproduction-kit-spec",
        "source": "E3.5_REPRODUCTION_KIT_SPEC.md",
        "declared_status": "SPECIFICATION_IMPLEMENTATION_INCOMPLETE",
        "ladder": "E3.5",
    },
    {
        "identity": "portfolio-e4-pending-witnessed-seal",
        "source": "PORTFOLIO_EVIDENCE_STATUS.md",
        "declared_status": "E4_NOT_EARNED",
        "ladder": "E4",
    },
    {
        "identity": "mathos-e4-runnable-computational-support",
        "source": "tools/mathos_bench/mathos_bench_claimset_key_v0_1.json",
        "declared_status": "DIFFERENT_LADDER",
        "ladder": "E4",
    },
    {
        "identity": "rc1-three-tool-policy-suite-absent",
        "source": "releases/weaver-witness-signed-rc1/README.md",
        "declared_status": "SOURCE_AND_TRANSCRIPT_ABSENT",
        "ladder": "RC1",
    },
)


def adjudication_record() -> dict[str, Any]:
    identities = [item["identity"] for item in DECLARED_POLICIES]
    return {
        "status": FREEZE_STATUS,
        "authority": AUTHORITY,
        "governing_policy": None,
        "release_target_frozen": False,
        "declared_policies": list(DECLARED_POLICIES),
        "distinct_identities": identities,
        "reason": (
            "E3.5 kit, portfolio E4, MathOS E4, and the RC1 witness packet "
            "do not name one governing witness policy. No identity is selected."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write the adjudication record as JSON")
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="Rejected while the discrepancy is unadjudicated.",
    )
    args = parser.parse_args(argv)
    record = adjudication_record()
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    if args.freeze:
        print(
            "REFUSED: witness policy freeze is withheld while declared "
            "versions disagree. No release target was selected.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
