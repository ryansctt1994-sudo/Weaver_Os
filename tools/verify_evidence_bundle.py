"""Read-only, independently implemented verifier for Weaver evidence bundles.

Checks file bytes and cross-file bindings without importing the generating
runner. DOES NOT authenticate a producer, verify execution, grant authority,
or qualify as independently witnessed reproduction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

REPORT_FILES = {"evidence-manifest.json", "verification-report.json", "report.json"}
REQUIRED = {
    "unit_and_integration",
    "bound_witness",
    "mutation_suite",
    "adversarial_corpus",
    "installed_wheel",
    "formal_tlc",
    "static_analysis_strict",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class BundleRefusal(ValueError):
    """Input cannot establish the claimed bundle byte integrity."""


def refuse(reason: str) -> None:
    raise BundleRefusal(reason)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in items:
        if name in result:
            refuse(f"duplicate JSON member: {name}")
        result[name] = value
    return result


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        refuse(f"non-finite JSON number: {token}")
    return value


def _json_bytes(data: bytes, origin: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data,
            object_pairs_hook=_pairs,
            parse_constant=lambda value: refuse(f"non-finite JSON value: {value}"),
            parse_float=_finite_float,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        refuse(f"invalid JSON in {origin}: {exc}")
    if not isinstance(value, dict):
        refuse(f"JSON object required: {origin}")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular_file(path: Path, *, anchor: Path) -> Path:
    if not path.is_relative_to(anchor):
        refuse(f"path outside admitted root: {path}")
    current = anchor
    if current.is_symlink():
        refuse(f"symlink root refused: {anchor}")
    for part in path.relative_to(anchor).parts:
        current = current / part
        if current.is_symlink():
            refuse(f"symlink refused: {current}")
    if not path.is_file():
        refuse(f"missing or non-file artifact: {path}")
    return path


def _safe_label(label: Any) -> str:
    if not isinstance(label, str) or not label or "\\" in label or ":" in label:
        refuse(f"unsafe evidence label: {label!r}")
    path = PurePosixPath(label)
    if path.is_absolute() or path.as_posix() != label:
        refuse(f"noncanonical evidence label: {label!r}")
    if any(part in {".", ".."} for part in label.split("/")):
        refuse(f"path traversal in evidence label: {label!r}")
    return label


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        refuse(f"invalid SHA-256 in {field}")
    return value


def _resolve_label(label: str, root: Path, output: Path) -> Path:
    label = _safe_label(label)
    # Source artifacts use repository-relative labels; external output files
    # use basenames. Ambiguity fails closed, including two equal-hash files.
    candidates = [root / label, output / label]
    unique: dict[Path, Path] = {}
    for candidate in candidates:
        if not candidate.is_file() and not candidate.is_symlink():
            continue
        anchor = root if candidate.is_relative_to(root) else output
        checked = _regular_file(candidate, anchor=anchor)
        unique[checked.resolve()] = checked
    if len(unique) != 1:
        refuse(f"missing or ambiguous evidence label: {label}")
    return next(iter(unique.values()))


def _output_label(filename: str, root: Path, output: Path) -> str:
    if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
        refuse(f"unsafe output filename: {filename!r}")
    target = output / filename
    if output.is_relative_to(root):
        return target.relative_to(root).as_posix()
    return filename


def verify_bundle(root: Path, output: Path) -> dict[str, Any]:
    """Verify report and manifest against current bytes without executing them.

    A successful result only proves local byte/structural consistency in the
    caller-supplied directories. Trust anchors and source authenticity are out
    of scope.
    """
    root = root.absolute()
    output = output.absolute()
    if root.is_symlink() or output.is_symlink():
        refuse("symlink root or output directory refused")
    if not root.is_dir() or not output.is_dir():
        refuse("root and output must be directories")

    manifest_data = _regular_file(output / "evidence-manifest.json", anchor=output).read_bytes()
    report_data = _regular_file(output / "verification-report.json", anchor=output).read_bytes()
    compatibility = _regular_file(output / "report.json", anchor=output).read_bytes()
    if report_data != compatibility:
        refuse("canonical and compatibility reports differ")

    manifest = _json_bytes(manifest_data, "evidence-manifest.json")
    report = _json_bytes(report_data, "verification-report.json")
    if set(manifest) != {"schema", "files"} or manifest["schema"] != "weaver-evidence-manifest-1":
        refuse("unsupported manifest schema or fields")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        refuse("empty or invalid evidence file map")
    if report.get("schema_version") != "1.0":
        refuse("unsupported verification report version")
    if report.get("scope") != "local-checks-not-independent-reproduction":
        refuse("unexpected assurance scope")

    schema_path = _regular_file(root / "schemas/verification_run.schema.json", anchor=root)
    schema = _json_bytes(schema_path.read_bytes(), "verification_run.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(report))
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path)
        refuse(f"report schema failure at {location or 'root'}: {errors[0].message}")

    digest = _digest(report["evidence_manifest_sha256"], "report.evidence_manifest_sha256")
    if _sha256(manifest_data) != digest:
        refuse("manifest digest does not match report")
    if report.get("artifact_hashes") != files:
        refuse("report and manifest artifact inventories differ")
    if "schemas/verification_run.schema.json" not in files:
        refuse("unbound verification report schema")
    if "requirements-verification.lock" not in files:
        refuse("unbound verification lockfile")

    resolved: dict[str, Path] = {}
    for label, expected in files.items():
        _safe_label(label)
        _digest(expected, f"files[{label}]")
        source = _resolve_label(label, root, output)
        if source.resolve() in (prior.resolve() for prior in resolved.values()):
            refuse(f"one artifact is assigned multiple labels: {label}")
        if _hash_file(source) != expected:
            refuse(f"artifact hash mismatch: {label}")
        resolved[label] = source

    # The producer deliberately excludes these generated reports from its
    # evidence manifest. Other direct output files must be represented.
    for path in output.iterdir():
        if path.name in REPORT_FILES:
            continue
        if path.is_symlink() or not path.is_file():
            refuse(f"unsafe or untracked output member: {path.name}")
        label = _output_label(path.name, root, output)
        if label not in resolved or resolved[label] != path:
            refuse(f"untracked output artifact: {path.name}")

    lock_hash = _digest(report["lockfile_sha256"], "report.lockfile_sha256")
    if lock_hash != files["requirements-verification.lock"]:
        refuse("lockfile report digest mismatch")

    by_name: dict[str, dict[str, Any]] = {}
    flattened: list[dict[str, Any]] = []
    for verifier in report["verifiers"]:
        name = verifier["name"]
        if name in by_name:
            refuse(f"duplicate verifier identity: {name}")
        by_name[name] = verifier
        if not verifier["steps"]:
            refuse(f"empty steps: {name}")
        for step in verifier["steps"]:
            log_name = step["log"]
            label = _output_label(log_name, root, output)
            if label not in resolved or resolved[label] != output / log_name:
                refuse(f"unbound step log: {name}/{log_name}")
            if files[label] != _digest(step["log_sha256"], "step.log_sha256"):
                refuse(f"step log digest mismatch: {name}/{log_name}")
            if (step["status"] == "PASS") != (step["exit_code"] == 0):
                refuse(f"step status disagrees with exit code: {name}")
            flattened.append(
                {
                    "verifier": name,
                    "step": step["step"],
                    "command": step["command"],
                    "exit_code": step["exit_code"],
                    "status": step["status"],
                }
            )
    if set(by_name) != REQUIRED or report["commands"] != flattened:
        refuse("required verifier set or flattened command transcript differs")

    adv_label = _output_label("adversarial-results.json", root, output)
    if adv_label not in resolved or resolved[adv_label] != output / "adversarial-results.json":
        refuse("unbound adversarial results document")
    adv_doc = _json_bytes((output / "adversarial-results.json").read_bytes(), adv_label)
    if adv_doc.get("schema") != "weaver-adversarial-results-1":
        refuse("unexpected adversarial document schema")
    baseline = adv_doc.get("baseline")
    if (
        not isinstance(baseline, dict)
        or baseline.get("status") != "PASS"
        or type(baseline.get("exit_code")) is not int
        or baseline["exit_code"] != 0
    ):
        refuse("adversarial baseline PASS is not bound to zero exit code")
    if adv_doc.get("results") != report["adversarial_results"]:
        refuse("adversarial results differ from verification report")
    cases = report["adversarial_results"]
    if {case["case_id"] for case in cases} != {f"ADV-{n:03d}" for n in range(1, 7)}:
        refuse("incomplete adversarial cases")
    for case in cases:
        fixture = _safe_label(case["fixture"])
        if "/" in fixture:
            refuse("adversarial fixture must be one filename")
        label = f"tests/fixtures/verification/{fixture}"
        if label not in resolved:
            refuse(f"unbound adversarial fixture: {fixture}")
        if files[label] != _digest(case["fixture_sha256"], "case.fixture_sha256"):
            refuse(f"adversarial fixture digest mismatch: {fixture}")

    wheels = [label for label in files if label.endswith(".whl")]
    if report["wheel_sha256"] is not None:
        if len(wheels) != 1 or files[wheels[0]] != report["wheel_sha256"]:
            refuse("wheel SHA-256 is not bound to exactly one artifact")
    elif report["overall_verdict"] == "PASS":
        refuse("PASS report without wheel binding")

    if report["overall_verdict"] == "PASS":
        if report["dirty"] or any(x["status"] != "PASS" for x in by_name.values()):
            refuse("PASS claim contradicts dirty tree or verifier failures")
        if any(x["status"] != "PASS" for x in cases):
            refuse("PASS claim contradicts adversarial failures")
        if adv_doc.get("status") != "PASS" or adv_doc.get("baseline", {}).get("status") != "PASS":
            refuse("PASS claim contradicts recorded adversarial baseline")
    else:
        refuse("producer overall verdict is not PASS; no positive bundle admission")

    return {
        "result": "BUNDLE_BYTES_CONSISTENT",
        "assurance": "LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION",
        "files_checked": len(files),
        "verifiers_checked": len(by_name),
        "adversarial_cases_checked": len(cases),
        "verified_commit_claim": report["verified_commit_sha"],
        "manifest_sha256": digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_bundle(args.root, args.output)
    except (BundleRefusal, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"result": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
