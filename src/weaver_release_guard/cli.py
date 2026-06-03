from __future__ import annotations

import argparse

from .provenance import cmd_generate, cmd_verify


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="weaver-release-guard")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate Weaver provenance JSON")
    g.add_argument("--dist-dir", default="dist")
    g.add_argument("--manifest", default="manifest.json")
    g.add_argument("--slsa", default="provenance.json")
    g.add_argument("--out", default="weaver_provenance.json")
    g.add_argument("--version", default="")
    g.add_argument("--build-id", default="")
    g.add_argument("--workflow", default="")
    g.add_argument("--runner", default="")
    g.add_argument("--started-at", default="")
    g.add_argument("--finished-at", default="")
    g.add_argument("--repo", default="")
    g.add_argument("--ref", default="")
    g.add_argument("--sha", default="")
    g.add_argument("--python-version", default="")
    g.add_argument("--policy-version", default="v0.5.1")
    g.add_argument("--lease-id", default="")
    g.add_argument("--authority-level", type=int, default=0)
    g.add_argument("--reviewer", default="")
    g.add_argument("--approval-ref", default="")
    g.add_argument("--signature-key-id", default="")
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("verify", help="Verify Weaver provenance")
    v.add_argument("artifact")
    v.add_argument("manifest")
    v.add_argument("weaver")
    v.add_argument("--slsa", default="")
    v.add_argument("--jwt", default="")
    v.set_defaults(func=cmd_verify)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
