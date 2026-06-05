"""Verify EGS receipt hash binding and exercise the negative-control path.

The verifier is intentionally narrow: if a receipt claims VERIFIED, it must cite
sha256 lines that exactly match the freshly computed manifest for the current
tree. Draft receipts may omit the hash block.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Mapping

ROOT = Path("governance/execution_substrate/egs_v1_0")
TARGETS = [
    ROOT / "specs" / "synthesis_state_machine.yaml",
    ROOT / "specs" / "execution_token.schema.json",
    ROOT / "specs" / "transition_table.md",
    ROOT / "specs" / "sm.py",
    ROOT / "specs" / "exec_token.py",
]
HASH_RE = re.compile(r"^([a-fA-F0-9]{64})\s{2}(.+)$")


def compute_manifest() -> dict[str, str]:
    return {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in TARGETS}


def write_manifest(path: Path, manifest: Mapping[str, str]) -> None:
    lines = [f"{digest}  {target}" for target, digest in sorted(manifest.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def receipt_claims_verified(text: str) -> bool:
    return "Status: VERIFIED" in text or "status: VERIFIED" in text


def parse_receipt_hashes(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        match = HASH_RE.match(line.strip())
        if match:
            digest, target = match.groups()
            parsed[target] = digest.lower()
    return parsed


def verify_receipt(text: str, manifest: Mapping[str, str]) -> tuple[bool, str]:
    if not receipt_claims_verified(text):
        return True, "draft receipt: no VERIFIED claim to bind"

    cited = parse_receipt_hashes(text)
    if not cited:
        return False, "VERIFIED receipt cites no sha256 lines"

    missing = sorted(set(manifest) - set(cited))
    extra = sorted(set(cited) - set(manifest))
    mismatched = sorted(path for path, digest in manifest.items() if cited.get(path) != digest)

    if missing or extra or mismatched:
        return False, f"hash binding failed; missing={missing}; extra={extra}; mismatched={mismatched}"
    return True, "VERIFIED receipt hash binding matches current tree"


def main() -> None:
    manifest = compute_manifest()
    manifest_path = ROOT / "receipts" / "EGS_v1_0.sha256"
    write_manifest(manifest_path, manifest)
    print(manifest_path.read_text(encoding="utf-8"))

    receipt_path = ROOT / "receipts" / "EGS_v1_0_draft_receipt.md"
    receipt_text = receipt_path.read_text(encoding="utf-8")
    ok, msg = verify_receipt(receipt_text, manifest)
    print(msg)
    if not ok:
        raise SystemExit(msg)

    bad_manifest_line = "0" * 64 + f"  {next(iter(manifest))}"
    negative_receipt = "Status: VERIFIED\n\nCI replay hash manifest:\n\n" + bad_manifest_line + "\n"
    negative_ok, negative_msg = verify_receipt(negative_receipt, manifest)
    if negative_ok:
        raise SystemExit("negative-control receipt unexpectedly passed")
    print(f"negative-control failed as expected: {negative_msg}")


if __name__ == "__main__":
    main()
