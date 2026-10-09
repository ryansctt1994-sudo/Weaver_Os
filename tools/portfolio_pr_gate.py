"""Audit a pinned GitHub PR snapshot before integration; never grant authority.

This deterministic checker detects same-repository file overlap and unverified
merge enforcement. The snapshot is input evidence, not live GitHub truth.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STATES = {"open", "closed"}


class SnapshotRefusal(ValueError):
    """Malformed or ambiguous review evidence."""


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in items:
        if key in obj:
            raise SnapshotRefusal(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def read_snapshot(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda x: _invalid_constant(x),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise SnapshotRefusal(f"cannot read snapshot: {exc}") from exc
    if not isinstance(document, dict):
        raise SnapshotRefusal("snapshot must be a JSON object")
    return document


def _invalid_constant(value: str) -> None:
    raise SnapshotRefusal(f"non-finite JSON constant: {value}")


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise SnapshotRefusal(f"invalid SHA in {field}")
    return value


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise SnapshotRefusal("invalid changed filename")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or parsed.as_posix() != value:
        raise SnapshotRefusal(f"noncanonical filename: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise SnapshotRefusal(f"unsafe filename: {value!r}")
    return value


def _validate_and_index(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if set(snapshot) != {"schema", "observed_date", "source", "repositories"}:
        raise SnapshotRefusal("unsupported or incomplete snapshot fields")
    if snapshot["schema"] != "weaver-pr-review-snapshot-v1":
        raise SnapshotRefusal("unsupported snapshot schema")
    if snapshot["source"] != "provider-metadata-as-observed":
        raise SnapshotRefusal("unsupported observation provenance label")
    date = snapshot["observed_date"]
    if not isinstance(date, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) is None:
        raise SnapshotRefusal("observed_date must be YYYY-MM-DD")
    repos = snapshot["repositories"]
    if not isinstance(repos, list) or not repos:
        raise SnapshotRefusal("empty or invalid repository inventory")

    seen_repos: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in repos:
        if not isinstance(item, dict) or set(item) != {
            "repository", "main_sha", "branch_protected", "repository_rulesets",
            "organization_rulesets_checked", "pull_requests",
        }:
            raise SnapshotRefusal("invalid repository record")
        name = item["repository"]
        if not isinstance(name, str) or not REPO.fullmatch(name) or name in seen_repos:
            raise SnapshotRefusal(f"invalid or duplicate repository: {name}")
        seen_repos.add(name)
        _sha(item["main_sha"], f"{name} main")
        if item["branch_protected"] not in (True, False, None):
            raise SnapshotRefusal("branch_protected must be boolean or null")
        rules = item["repository_rulesets"]
        if rules is not None and (not isinstance(rules, int) or isinstance(rules, bool) or rules < 0):
            raise SnapshotRefusal("repository_rulesets must be nonnegative integer or null")
        if type(item["organization_rulesets_checked"]) is not bool:
            raise SnapshotRefusal("organization_rulesets_checked must be boolean")
        prs = item["pull_requests"]
        if not isinstance(prs, list):
            raise SnapshotRefusal("pull_requests must be a list")
        seen_prs: set[int] = set()
        for pr in prs:
            if not isinstance(pr, dict) or set(pr) != {
                "number", "head_sha", "base_sha", "state", "draft", "merged", "files",
            }:
                raise SnapshotRefusal(f"malformed pull request in {name}")
            num = pr["number"]
            if type(num) is not int or num < 1 or num in seen_prs:
                raise SnapshotRefusal(f"invalid or duplicate PR number in {name}")
            seen_prs.add(num)
            _sha(pr["head_sha"], f"{name} PR #{num} head")
            _sha(pr["base_sha"], f"{name} PR #{num} base")
            if pr["state"] not in STATES:
                raise SnapshotRefusal("invalid PR state")
            if type(pr["draft"]) is not bool or type(pr["merged"]) is not bool:
                raise SnapshotRefusal("draft and merged must be booleans")
            if pr["merged"] and pr["state"] != "closed":
                raise SnapshotRefusal("merged PR cannot be open")
            paths = pr["files"]
            if not isinstance(paths, list) or not paths:
                raise SnapshotRefusal(f"missing changed files for {name} PR #{num}")
            checked = [_path(v) for v in paths]
            if len(set(checked)) != len(checked):
                raise SnapshotRefusal(f"duplicate path in {name} PR #{num}")
        normalized.append(item)
    return normalized


def audit_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    repositories = _validate_and_index(snapshot)
    findings: list[dict[str, Any]] = []
    reviewed = 0
    for repo in sorted(repositories, key=lambda item: item["repository"]):
        name = repo["repository"]
        # This is a missing-assurance signal, not proof of organization-wide
        # absence of enforcement; organization-level rules are not inspected.
        if repo["branch_protected"] is not True:
            findings.append({
                "kind": "BRANCH_PROTECTION_NOT_CONFIRMED",
                "repository": name,
                "detail": "main branch protection is false or unknown in provider metadata",
            })
        if (
            repo["repository_rulesets"] in (None, 0)
            and not repo["organization_rulesets_checked"]
        ):
            findings.append({
                "kind": "EFFECTIVE_RULESETS_UNVERIFIED",
                "repository": name,
                "detail": "repo rulesets absent or unknown; organization rules not audited",
            })
        path_owners: dict[str, list[int]] = defaultdict(list)
        for pr in repo["pull_requests"]:
            if pr["state"] != "open" or pr["merged"]:
                continue
            reviewed += 1
            num = pr["number"]
            if pr["base_sha"] != repo["main_sha"]:
                findings.append({
                    "kind": "BASE_SHA_STALE",
                    "repository": name,
                    "pull_requests": [num],
                    "detail": f"PR base {pr['base_sha']} differs from observed main",
                })
            if pr["draft"]:
                findings.append({
                    "kind": "DRAFT_NOT_ADMITTED",
                    "repository": name,
                    "pull_requests": [num],
                    "detail": "draft review branch, not an integration-ready merge",
                })
            for path in pr["files"]:
                path_owners[path].append(num)
        for path, owners in sorted(path_owners.items()):
            if len(owners) > 1:
                findings.append({
                    "kind": "OVERLAPPING_OPEN_PR_PATH",
                    "repository": name,
                    "path": path,
                    "pull_requests": sorted(owners),
                    "detail": "overlap needs combined source and CI replay, not automatic conflict inference",
                })
    findings.sort(
        key=lambda f: (
            f["repository"], f["kind"], f.get("path", ""),
            f.get("pull_requests", []),
        )
    )
    return {
        "schema": "weaver-pr-integration-audit-v1",
        "observed_date": snapshot["observed_date"],
        "result": "HOLD" if findings else "REVIEW_REQUIRED",
        "not_authorized": True,
        "assurance": "PROVIDER_METADATA_SNAPSHOT_ONLY",
        "repositories_checked": len(repositories),
        "open_prs_reviewed": reviewed,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--fail-on-hold", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit_snapshot(read_snapshot(args.snapshot))
    except SnapshotRefusal as exc:
        print(json.dumps({"result": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return int(args.fail_on_hold and result["result"] == "HOLD")


if __name__ == "__main__":
    raise SystemExit(main())
