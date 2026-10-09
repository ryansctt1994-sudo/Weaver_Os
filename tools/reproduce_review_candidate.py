"""Reproduce an exact review commit locally; never mint witness authority.

Operator workflow: detached clean source -> execute complete verifier ->
separately check evidence bundle bytes -> emit bounded local JSON record.

The expected commit must arrive independently of this repository: never
derive it from the checkout that the verifier is supposed to challenge.
This tool DOES NOT prove independent operator identity or authenticity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from tools.verify_evidence_bundle import verify_bundle

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = "LOCAL_EXECUTION_NO_AUTHENTICATED_WITNESS"
ASSURANCE = "LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION"


class ReproductionRefusal(ValueError):
    """A source, execution, or evidence condition failed closed."""


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ReproductionRefusal(f"git command unavailable: {args!r}") from exc
    if type(result.returncode) is not int or result.returncode != 0:
        raise ReproductionRefusal(f"git command refused: {args!r}")
    return result.stdout.strip()


def _verify_tracked_source(root: Path, expected_head: str) -> None:
    """Compare raw worktree bytes to commit blobs without consulting index flags.

    This exact-source profile admits ordinary files only. Symlinks, gitlinks,
    missing files, clean-filter conversions, and executable-mode drift refuse.
    It is a pre/post snapshot check, not an atomic or sandboxed execution proof.
    """
    listing = _git(root, "ls-tree", "-r", "-z", "--full-tree", expected_head)
    if not listing or not listing.endswith("\0"):
        raise ReproductionRefusal("tracked source tree is empty or malformed")
    for entry in listing[:-1].split("\0"):
        metadata, separator, name = entry.partition("\t")
        fields = metadata.split(" ")
        relative = PurePosixPath(name)
        if (
            not separator
            or len(fields) != 3
            or not name
            or relative.is_absolute()
            or relative.as_posix() != name
            or ".." in relative.parts
            or "\\" in name
        ):
            raise ReproductionRefusal("tracked source tree contains an unsafe entry")
        mode, kind, expected_blob = fields
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ReproductionRefusal(f"unsupported tracked source type: {name!r}")
        if SHA_RE.fullmatch(expected_blob) is None:
            raise ReproductionRefusal("tracked source blob identity is malformed")
        path = root.joinpath(*relative.parts)
        try:
            parent = root
            for part in relative.parts[:-1]:
                parent = parent / part
                if not stat.S_ISDIR(parent.lstat().st_mode):
                    raise ReproductionRefusal(f"unsafe tracked source parent: {name!r}")
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ReproductionRefusal(f"nonregular tracked source file: {name!r}")
            if bool(info.st_mode & 0o111) != (mode == "100755"):
                raise ReproductionRefusal(f"tracked source executable mode differs: {name!r}")
            data = path.read_bytes()
        except OSError as exc:
            raise ReproductionRefusal(f"tracked source file unavailable: {name!r}") from exc
        # Git SHA-1 object IDs bind a type/length header and the raw blob bytes.
        actual_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual_blob != expected_blob:
            raise ReproductionRefusal(f"tracked source bytes differ: {name!r}")


def preflight(root: Path, expected_head: str) -> str:
    """Admit only the caller-pinned, clean, detached, exact Git source."""
    if SHA_RE.fullmatch(expected_head) is None:
        raise ReproductionRefusal("expected-head must be a full lowercase 40-hex Git SHA")
    root = root.resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise ReproductionRefusal("checkout is not the expected repository root")
    actual = _git(root, "rev-parse", "--verify", "HEAD")
    if actual != expected_head:
        raise ReproductionRefusal(f"source mismatch: {actual} != {expected_head}")
    # A symbolic ref exists only for an attached branch.
    attached = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "-q", "HEAD"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if attached.returncode not in (0, 1):
        raise ReproductionRefusal("unable to verify detached source checkout")
    if attached.returncode == 0:
        raise ReproductionRefusal("source must be checked out detached at exact commit")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReproductionRefusal("source checkout is dirty or contains untracked files")
    _verify_tracked_source(root, expected_head)
    return actual


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reproduce(root: Path, expected_head: str) -> dict[str, Any]:
    """Execute the entire origin-controlled gate and recheck final bytes."""
    root = root.resolve()
    checked = preflight(root, expected_head)
    output = root / "verification-output"
    if output.exists() or output.is_symlink():
        raise ReproductionRefusal("refuse stale verification-output; use a fresh checkout")

    # GitHub Actions merge-checkout identities must not leak into an operator
    # run or impersonate the independently supplied exact source commit.
    sanitized = os.environ.copy()
    for key in (
        "GITHUB_SHA",
        "GITHUB_REF",
        "WEAVER_SOURCE_HEAD_SHA",
        "WEAVER_BASE_SHA",
        "PYTHONPATH",
        "PYTHONHOME",
    ):
        sanitized.pop(key, None)
    command = [sys.executable, "-m", "tools.verify_all", "--output", str(output)]
    try:
        executed = subprocess.run(
            command,
            cwd=root,
            env=sanitized,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReproductionRefusal("complete verifier failed to execute") from exc
    if type(executed.returncode) is not int or executed.returncode != 0:
        raise ReproductionRefusal(
            "complete verifier refused; see verification-output logs "
            f"(exit={executed.returncode!r})"
        )

    # This consumer reads and re-hashes final bytes independently of the
    # producer; it is not an independently operated witness.
    result = verify_bundle(root, output)
    if (
        result.get("result") != "BUNDLE_BYTES_CONSISTENT"
        or result.get("assurance") != ASSURANCE
        or result.get("verifiers_checked") != 7
        or result.get("adversarial_cases_checked") != 6
    ):
        raise ReproductionRefusal("bundle verifier did not return its bounded expected result")

    report_path = output / "verification-report.json"
    try:
        report = json.loads(report_path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise ReproductionRefusal("missing or malformed final verification report") from exc
    if not isinstance(report, dict) or any(
        report.get(key) != checked for key in ("source_head_sha", "verified_commit_sha")
    ):
        raise ReproductionRefusal("report does not bind both commit claims to checkout HEAD")
    if report.get("dirty") is not False or report.get("overall_verdict") != "PASS":
        raise ReproductionRefusal("report does not establish a clean, successful local gate")
    manifest_hash = result.get("manifest_sha256")
    if (
        not isinstance(manifest_hash, str)
        or SHA256_RE.fullmatch(manifest_hash) is None
        or _sha256(output / "evidence-manifest.json") != manifest_hash
    ):
        raise ReproductionRefusal("final manifest digest is unbound")

    # Reject source alteration during execution rather than relying on only
    # the start-of-run dirty flag and Git SHA.
    if preflight(root, expected_head) != checked:
        raise ReproductionRefusal("source changed after verification")

    return {
        "schema": "weaver-operator-reproduction-local-v1",
        "result": "LOCAL_VERIFICATION_REPRODUCED",
        "scope": SCOPE,
        "source": {
            "expected_commit_sha": expected_head,
            "observed_commit_sha": checked,
            "tracked_source_binding": "GIT_BLOB_BYTES_AND_EXECUTABLE_MODE_PRE_POST",
            "tool_sha256": _sha256(root / "tools/reproduce_review_candidate.py"),
            "lockfile_sha256": _sha256(root / "requirements-verification.lock"),
        },
        "environment": {"python": sys.version, "platform": platform.platform()},
        "evidence": {
            "manifest_sha256": manifest_hash,
            "report_sha256": _sha256(report_path),
            "files_checked": result["files_checked"],
            "verifiers_checked": 7,
            "adversarial_cases_checked": 6,
        },
        "trust": {
            "authenticated_witness": False,
            "independence_verified": False,
            "signature_verified": False,
            "evidence_ceiling": "E2",
            "witness": "W0",
            "operational_authority": "O0_WITHHELD",
            "production": "PROHIBITED",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-head", required=True, help="Full frozen SHA from outside checkout"
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        result = reproduce(root, args.expected_head)
    except (ReproductionRefusal, ValueError, OSError) as exc:
        print(f"REPRODUCTION_REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
