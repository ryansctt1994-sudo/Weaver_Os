"""Command-line interface for offline verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chronicle import Chronicle
from .promotion import EvidenceLevel, evaluate_promotion


def _verify_chronicle(args: argparse.Namespace) -> int:
    report = Chronicle(args.path).verify()
    print(json.dumps(report.__dict__, indent=2, sort_keys=True))
    return 0 if report.valid else 1


def _checkpoint(args: argparse.Namespace) -> int:
    print(json.dumps(Chronicle(args.path).checkpoint(), indent=2, sort_keys=True))
    return 0


def _promote(args: argparse.Namespace) -> int:
    level = EvidenceLevel[args.level]
    decision = evaluate_promotion(level, args.evidence)
    print(
        json.dumps(
            {
                "granted": decision.granted,
                "requested": decision.requested.name,
                "missing": list(decision.missing),
                "reason": decision.reason,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if decision.granted else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weaver-assurance")
    commands = parser.add_subparsers(required=True)

    verify = commands.add_parser("verify-chronicle")
    verify.add_argument("path", type=Path)
    verify.set_defaults(func=_verify_chronicle)

    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("path", type=Path)
    checkpoint.set_defaults(func=_checkpoint)

    promote = commands.add_parser("promote")
    promote.add_argument("level", choices=[level.name for level in EvidenceLevel])
    promote.add_argument("--evidence", action="append", default=[])
    promote.set_defaults(func=_promote)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

