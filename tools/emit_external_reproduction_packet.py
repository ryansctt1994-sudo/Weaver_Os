"""Emit a local reproduction packet that cannot promote evidence.

The packet binds source identities and file digests observed on this machine.
It does not authenticate a GitHub Actions run, a witness, or a policy key.
A caller that asks this tool to claim a witness is refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PACKET_VERSION = "external-reproduction-packet-v1"
SCOPE = "LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION"
PINNED_HEAD = "e2232fcb2bb70e1535c43750429baa719fed815b"
P0_006_HEAD = "36b49fa8cd324e49f968ab65db3b443b31d565c4"
RED_HEAD = "9673528657ce8663499c51c1d3817ac2e7d29e57"

SOURCE_FILES = (
    "tools/verify_all.py",
    "tools/verify_evidence_bundle.py",
    "schemas/verification_run.schema.json",
    "docs/P0_007_ADVERSARIAL_RESULT_BINDING.md",
)

HOSTED_RUN_CLAIMS = (
    {
        "name": "RED Python 3.12 tests",
        "run_id": 37881830619,
        "commit": RED_HEAD,
        "status": "UNAUTHENTICATED_CLAIM",
    },
    {
        "name": "GREEN Python 3.12 tests",
        "run_id": 37882028359,
        "commit": PINNED_HEAD,
        "status": "UNAUTHENTICATED_CLAIM",
    },
    {
        "name": "verification evidence",
        "run_id": 37882028357,
        "commit": PINNED_HEAD,
        "status": "UNAUTHENTICATED_CLAIM",
    },
)

MISSING_TRUST_ANCHORS = (
    "independently_authenticated_witness",
    "signed_attestation_over_artifact_digest",
    "verifier_identity_bound_to_expected_key",
    "enforced_branch_ruleset",
    "adjudicated_witness_policy_version",
    "external_rewrite_anchor",
)


class PacketError(ValueError):
    """Raised when a reproduction packet cannot be emitted honestly."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def build_packet(root: Path, observed_head: str | None) -> dict[str, Any]:
    """Build a fail-closed local packet. Missing source files are recorded."""
    if not root.is_dir():
        raise PacketError(f"root is not a directory: {root}")

    files: list[dict[str, str]] = []
    missing: list[str] = []
    for relative in SOURCE_FILES:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        files.append({"path": relative, "sha256": _sha256(path)})

    head = observed_head or ""
    packet: dict[str, Any] = {
        "packet_version": PACKET_VERSION,
        "scope": SCOPE,
        "authenticated_attestation": False,
        "witness_claimed": False,
        "authority": {
            "evidence_ceiling": "E2",
            "witness": "W0",
            "operator": "O0",
            "promotion": "WITHHELD",
            "production": "PROHIBITED",
        },
        "source_identities": {
            "pinned_review_head": PINNED_HEAD,
            "observed_head": head,
            "pinned_head_match": head == PINNED_HEAD,
            "p0_006_dependency": P0_006_HEAD,
            "red_test_commit": RED_HEAD,
            "repository": "ryansctt1994-sudo/Weaver_Os",
            "review_pull_request": 87,
        },
        "source_files": files,
        "missing_source_files": missing,
        "hosted_run_claims": list(HOSTED_RUN_CLAIMS),
        "missing_trust_anchors": list(MISSING_TRUST_ANCHORS),
        "ruleset_enforcement": "NOT_ESTABLISHED",
        "witness_policy_adjudication": "WITHHELD",
        "packet_complete": not missing,
    }
    return packet


def render_packet(packet: dict[str, Any]) -> str:
    return json.dumps(packet, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to hash")
    parser.add_argument("--output", help="Write the packet JSON to this path")
    parser.add_argument("--observed-head", default="", help="Observed git HEAD")
    parser.add_argument(
        "--require-pinned-head",
        action="store_true",
        help="Fail unless the observed HEAD is the pinned review commit",
    )
    parser.add_argument(
        "--claim-witness",
        action="store_true",
        help="Rejected. This tool cannot create witness evidence.",
    )
    args = parser.parse_args(argv)

    if args.claim_witness:
        print(
            "REFUSED: this packet cannot claim an independent witness. "
            "Authority remains E2 | W0 | O0 WITHHELD.",
            file=sys.stderr,
        )
        return 2

    packet = build_packet(Path(args.root), args.observed_head or None)
    if args.require_pinned_head and not packet["source_identities"]["pinned_head_match"]:
        print(
            "REFUSED: observed HEAD does not match pinned review commit "
            f"{PINNED_HEAD}.",
            file=sys.stderr,
        )
        return 1
    if not packet["packet_complete"]:
        print(
            "INCOMPLETE: missing source files: "
            + ", ".join(packet["missing_source_files"]),
            file=sys.stderr,
        )
        rendered = render_packet(packet)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 1

    rendered = render_packet(packet)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
