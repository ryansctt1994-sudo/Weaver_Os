"""governance.claim_audit: find claims a repository makes that its evidence doesn't back.

Scans every tracked text file (and every file path) for blocked terms, such
as "production-ready" or "validated", and classifies each occurrence:

  denied   the surrounding sentence negates it ("No production authority is
           claimed"), or, for a list item / table row / code-block line, its
           heading or lead-in sentence does ("Blocked until evidence exists:")
  backed   a claims-config entry backs it with evidence files that exist
  waived   a claims-config waiver accepts it, with a reason (counted as debt)
  claim    none of the above: an unbacked claim

Blocked terms come from the target's governance/open_gap_ledger.md
"Blocking Rule" block when it has one, so governance stays the source of
truth. Otherwise a default list mirroring that rule is used. A second "watch"
list (immutable, tamper-proof, guaranteed, ...) produces warnings only.

Exit status: 0 = no errors, 1 = errors found, 2 = refused (bad input).

The negation test is a heuristic. It works on sentences, not meaning, so a
sentence like "not only safe but certified" reads as a denial. Treat the
report as a review aid that blocks the obvious cases, not as proof that a
repository makes no overclaims.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SKILL_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.claim_audit.legacy_canonical import JCS_RFC8785, profiled_sha256  # noqa: E402

SKILL_ID = "governance.claim_audit"
SKILL_VERSION = "0.1.0"
REPORT_VERSION = "weaver.skill.claim_audit.report.v1"

# Mirrors the Blocking Rule in Weaver--Cathedral-'s governance/open_gap_ledger.md.
DEFAULT_BLOCKED = [
    "production-ready",
    "certified",
    "validated",
    "safe",
    "secure",
    "autonomous",
    "AGI",
    "ASI",
    "clinical",
    "legal authority",
    "defense-ready",
    "independently verified",
]
DEFAULT_WATCH = [
    "immutable",
    "tamper-proof",
    "tamper-evident",
    "guarantee",
    "guarantees",
    "guaranteed",
    "provably",
    "proven",
    "falsifiable",
    "unbreakable",
    "bulletproof",
    "military-grade",
]
LEDGER = "governance/open_gap_ledger.md"
CONFIG_CANDIDATES = ("governance/claims.json", "claims.json")
DEFAULT_EXCLUDE = [
    ".git/**",
    "node_modules/**",
    "**/node_modules/**",
    "dist/**",
    "build/**",
    "package-lock.json",
    "*.lock",
    "**/*.min.js",
]
MAX_BYTES = 2_000_000
# A negation only counts when it is this close to the term, so one "not" in a
# long, unpunctuated paragraph can't deny everything in it.
NEGATION_WINDOW_WORDS = 12

NEGATION = re.compile(
    r"\b(not|no|never|none|nor|neither|without|cannot|can't|isn't|aren't|doesn't|don't|won't|"
    r"denied|denies|deny|blocked|blocking|block|prohibited|forbidden|absent|until|unless|lacks|"
    r"not_established|not_yet|unverified|unclaimed|rather than|instead of)\b",
    re.IGNORECASE,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9*`\"'(\[])")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
FENCE = re.compile(r"^\s*(```|~~~)")


class Refusal(Exception):
    """Input is invalid; the skill refuses rather than guess (exit 2)."""


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    term: str
    severity: str  # "error" | "warning"
    category: str  # claim | denied | backed | waived | path_claim | evidence_missing | stale_entry
    text: str
    rule: str


# --- Terms ------------------------------------------------------------------


def _term_pattern(term: str) -> re.Pattern:
    words = [re.escape(w) for w in re.split(r"[-\s]+", term)]
    body = r"[-\s]+".join(words)
    flags = 0 if term.isupper() else re.IGNORECASE  # acronyms are case-sensitive: ASI, not "asi"
    # A hyphen may precede the term ("Z3-validated" is still a claim); a word
    # character may not ("invalidated" is not "validated").
    return re.compile(rf"(?<!\w){body}(?![\w-])", flags)


NEGATING_PREFIX = re.compile(r"(?:^|[^\w-])(?:non|un|not|pre)-$", re.IGNORECASE)


def blocked_terms_from_ledger(root: Path) -> list[str] | None:
    path = root / LEDGER
    if not path.is_file():
        return None
    text = _read_text(path, root)
    if text is None:
        raise Refusal("ledger is not a bounded local text file")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+Blocking Rule\s*$", line.strip()):
            for j in range(i + 1, len(lines)):
                if FENCE.match(lines[j]):
                    terms: list[str] = []
                    for k in range(j + 1, len(lines)):
                        if FENCE.match(lines[k]):
                            return terms or None
                        if lines[k].strip():
                            terms.append(lines[k].strip())
                    return None
    return None


# --- Config -----------------------------------------------------------------


def load_config(root: Path, explicit: Path | None) -> tuple[dict, str | None]:
    path = explicit
    if path is None:
        for candidate in CONFIG_CANDIDATES:
            if (root / candidate).is_file():
                path = root / candidate
                break
    if path is None:
        return {"exclude": [], "backed_claims": [], "waivers": []}, None
    try:
        text = _read_text(Path(path), root if explicit is None else None)
        if text is None:
            raise Refusal("claims config is not a bounded regular text file")
        config = json.loads(text)
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        raise Refusal(f"claims config {path} unreadable: {exc}") from exc
    _validate_config(config, path)
    config.setdefault("exclude", [])
    config.setdefault("backed_claims", [])
    config.setdefault("waivers", [])
    return config, str(path)


def _validate_config(config: Any, path: Path) -> None:
    def need(cond: bool, msg: str) -> None:
        if not cond:
            raise Refusal(f"claims config {path}: {msg}")

    need(isinstance(config, dict), "must be a JSON object")
    need(
        set(config)
        <= {"$schema", "version", "exclude", "backed_claims", "waivers", "extra_watch_terms"},
        "unknown keys "
        + str(
            sorted(
                set(config)
                - {"$schema", "version", "exclude", "backed_claims", "waivers", "extra_watch_terms"}
            )
        ),
    )
    need(config.get("version", 1) == 1, "version must be 1")
    for e in config.get("exclude", []):
        need(
            isinstance(e, dict)
            and isinstance(e.get("glob"), str)
            and isinstance(e.get("reason"), str)
            and e["reason"].strip(),
            "each exclude needs a glob and a non-empty reason",
        )
    for b in config.get("backed_claims", []):
        need(
            isinstance(b, dict)
            and all(isinstance(b.get(k), str) and b[k] for k in ("term", "file", "contains")),
            "each backed claim needs term, file, contains",
        )
        need(
            isinstance(b.get("evidence"), list)
            and b["evidence"]
            and all(isinstance(x, str) for x in b["evidence"]),
            "each backed claim needs a non-empty evidence list",
        )
    for w in config.get("waivers", []):
        need(
            isinstance(w, dict)
            and all(
                isinstance(w.get(k), str) and w[k].strip()
                for k in ("term", "file", "contains", "reason")
            ),
            "each waiver needs term, file, contains, reason",
        )
    need(
        all(isinstance(t, str) and t for t in config.get("extra_watch_terms", [])),
        "extra_watch_terms must be strings",
    )


# --- Files ------------------------------------------------------------------


def list_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        ).stdout
        files = [f for f in out.decode("utf-8", "replace").split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    return sorted(files)


def _excluded(rel: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch("/" + rel, g) for g in globs)


def _read_text(path: Path, root: Path | None = None) -> str | None:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        if root is not None:
            base = root.resolve()
            relative = path.absolute().relative_to(base)
            current = base
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    return None
            if not path.resolve().is_relative_to(base):
                return None
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except (OSError, ValueError, RuntimeError):
        return None
    if len(data) > MAX_BYTES or b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


# --- Context ----------------------------------------------------------------


@dataclass
class Unit:
    """A sentence-bearing span: a paragraph, list item, table row or code line."""

    start: int  # 0-based first line
    lines: list[str]
    kind: str  # paragraph | item | row | code | line | heading
    heading: str
    lead_in: str


def split_units(text: str, markdown: bool) -> list[Unit]:
    units: list[Unit] = []
    heading, lead_in, in_code = "", "", False
    para: list[str] = []
    para_start = 0

    def flush() -> None:
        nonlocal para, lead_in
        if para:
            units.append(Unit(para_start, para, "paragraph", heading, lead_in))
            lead_in = " ".join(para)
            para = []

    for i, line in enumerate(text.splitlines()):
        if not markdown:
            units.append(Unit(i, [line], "paragraph", "", ""))
            continue
        if FENCE.match(line):
            flush()
            in_code = not in_code
            continue
        if in_code:
            units.append(Unit(i, [line], "code", heading, lead_in))
            continue
        m = HEADING.match(line)
        if m:
            flush()
            heading, lead_in = m.group(1), ""
            units.append(Unit(i, [line], "heading", heading, ""))
            continue
        if not line.strip():
            flush()
            continue
        if line.lstrip().startswith("|"):
            flush()
            units.append(Unit(i, [line], "row", heading, lead_in))
            continue
        if LIST_ITEM.match(line):
            flush()
            units.append(Unit(i, [line], "item", heading, lead_in))
            continue
        if units and units[-1].kind == "item" and not para and line.startswith((" ", "\t")):
            units[-1].lines.append(line)  # wrapped list item
            continue
        if not para and line.startswith(("    ", "\t")):
            # Indented code (Markdown's rule): one unit per line, so code is never
            # joined into a "sentence" with its neighbours.
            units.append(Unit(i, [line], "line", heading, ""))
            continue
        if not para:
            para_start = i
        para.append(line)
    flush()
    return units


def _sentence_containing(unit_text: str, offset: int) -> str:
    pos = 0
    for sentence in SENTENCE_SPLIT.split(unit_text):
        start = unit_text.find(sentence, pos)
        end = start + len(sentence)
        if start <= offset < end:
            return sentence
        pos = end
    return unit_text


def _negated_near(text: str, start: int, end: int) -> bool:
    for neg in NEGATION.finditer(text):
        lo, hi = (neg.end(), start) if neg.end() <= start else (end, neg.start())
        if len(text[lo:hi].split()) <= NEGATION_WINDOW_WORDS:
            return True
    return False


def is_denied(unit: Unit, unit_text: str, start: int, end: int) -> bool:
    if NEGATING_PREFIX.search(unit_text[max(0, start - 5) : start]):
        return True  # "non-validated", "un-certified", "pre-production-ready"
    if unit.kind == "row":
        return bool(NEGATION.search(unit_text))  # a table row is one record
    sentence = _sentence_containing(unit_text, start)
    offset = unit_text.find(sentence) if sentence in unit_text else 0
    if _negated_near(sentence, start - offset, end - offset):
        return True
    if unit.kind in ("item", "code"):
        return bool(NEGATION.search(unit.heading) or NEGATION.search(unit.lead_in))
    return False


def python_units(text: str) -> list[Unit] | None:
    """Comments and string literals only: identifiers like `validated = ...` aren't claims."""
    kinds = {tokenize.COMMENT, tokenize.STRING}
    if hasattr(tokenize, "FSTRING_MIDDLE"):
        kinds.add(tokenize.FSTRING_MIDDLE)
    units = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in kinds:
                units.append(
                    Unit(tok.start[0] - 1, tok.string.splitlines() or [""], "paragraph", "", "")
                )
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return None
    return units


# --- Audit ------------------------------------------------------------------


def audit(root: Path, config_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise Refusal(f"root {root} is not a directory")
    config, config_used = load_config(root, config_path)

    ledger_terms = blocked_terms_from_ledger(root)
    blocked = ledger_terms or DEFAULT_BLOCKED
    watch = [
        t
        for t in DEFAULT_WATCH + config.get("extra_watch_terms", [])
        if t.lower() not in {b.lower() for b in blocked}
    ]
    patterns = [(t, "error", _term_pattern(t)) for t in blocked] + [
        (t, "warning", _term_pattern(t)) for t in watch
    ]
    globs = DEFAULT_EXCLUDE + [e["glob"] for e in config["exclude"]]
    # The config necessarily quotes the claims it backs or waives; never audit it.
    config_rel = _relative(config_used, root) if config_used else None
    if config_rel:
        globs.append(config_rel)

    findings: list[Finding] = []
    backed_hits = [0] * len(config["backed_claims"])
    waiver_hits = [0] * len(config["waivers"])
    scanned = 0

    def resolve(f: Finding, full_line: str | None = None) -> Finding:
        # Match against the whole line: f.text is truncated for the report, and
        # a term past the cut would otherwise never match its entry.
        line = full_line if full_line is not None else f.text
        for idx, b in enumerate(config["backed_claims"]):
            if (
                b["term"].lower() == f.term.lower()
                and fnmatch.fnmatch(f.file, b["file"])
                and b["contains"] in line
            ):
                backed_hits[idx] += 1
                missing = [e for e in b["evidence"] if not (root / e).exists()]
                if missing:
                    return Finding(
                        f.file,
                        f.line,
                        f.term,
                        "error",
                        "evidence_missing",
                        f.text,
                        f"backed_claims[{idx}] evidence not found: {missing}",
                    )
                return Finding(
                    f.file,
                    f.line,
                    f.term,
                    "info",
                    "backed",
                    f.text,
                    f"backed_claims[{idx}]: {', '.join(b['evidence'])}",
                )
        for idx, w in enumerate(config["waivers"]):
            if (
                w["term"].lower() == f.term.lower()
                and fnmatch.fnmatch(f.file, w["file"])
                and w["contains"] in line
            ):
                waiver_hits[idx] += 1
                return Finding(
                    f.file,
                    f.line,
                    f.term,
                    "info",
                    "waived",
                    f.text,
                    f"waivers[{idx}]: {w['reason']}",
                )
        return f

    for rel in list_files(root):
        if _excluded(rel, globs):
            continue
        for term, severity, pat in patterns:
            if pat.search(rel.replace("_", " ")):  # in names, "_" separates words
                findings.append(
                    resolve(Finding(rel, 0, term, severity, "path_claim", rel, "term in file path"))
                )
        text = _read_text(root / rel, root)
        if text is None:
            continue
        scanned += 1
        lines = text.splitlines()
        markdown = (
            rel.lower().endswith((".md", ".markdown", ".txt", ".rst")) or "." not in Path(rel).name
        )
        units = python_units(text) if rel.endswith(".py") else None
        for unit in units if units is not None else split_units(text, markdown):
            unit_text = " ".join(s.strip() for s in unit.lines)
            for term, severity, pat in patterns:
                for m in pat.finditer(unit_text):
                    # map the offset back to a line within the unit
                    consumed, line_no = 0, unit.start
                    for k, raw in enumerate(unit.lines):
                        piece = len(raw.strip()) + 1
                        if m.start() < consumed + piece:
                            line_no = unit.start + k
                            break
                        consumed += piece
                    full_line = lines[line_no].strip() if line_no < len(lines) else unit_text
                    snippet = full_line[:240]
                    if is_denied(unit, unit_text, m.start(), m.end()):
                        findings.append(
                            Finding(
                                rel,
                                line_no + 1,
                                term,
                                "info",
                                "denied",
                                snippet,
                                "negated in context",
                            )
                        )
                    else:
                        findings.append(
                            resolve(
                                Finding(
                                    rel,
                                    line_no + 1,
                                    term,
                                    severity,
                                    "claim",
                                    snippet,
                                    "unbacked claim",
                                ),
                                full_line,
                            )
                        )

    for idx, hits in enumerate(backed_hits):
        if not hits:
            b = config["backed_claims"][idx]
            findings.append(
                Finding(
                    b["file"],
                    0,
                    b["term"],
                    "error",
                    "stale_entry",
                    b["contains"],
                    f"backed_claims[{idx}] matches nothing",
                )
            )
    for idx, hits in enumerate(waiver_hits):
        if not hits:
            w = config["waivers"][idx]
            findings.append(
                Finding(
                    w["file"],
                    0,
                    w["term"],
                    "error",
                    "stale_entry",
                    w["contains"],
                    f"waivers[{idx}] matches nothing",
                )
            )

    findings = sorted(set(findings), key=lambda f: (f.file, f.line, f.term, f.category))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "skill_id": SKILL_ID,
        "skill_version": SKILL_VERSION,
        "root": root.name,
        "git_commit": _git_commit(root),
        "terms_source": LEDGER if ledger_terms else "default",
        "blocked_terms": blocked,
        "watch_terms": watch,
        "config": _relative(config_used, root),
        "config_sha256": hashlib.sha256(Path(config_used).read_bytes()).hexdigest()
        if config_used
        else None,
        "files_scanned": scanned,
        "counts": dict(sorted(counts.items())),
        "errors": errors,
        "warnings": warnings,
        "waiver_debt": counts.get("waived", 0),
        "passed": errors == 0,
        "findings": [asdict(f) for f in findings],
        "hash_profile": JCS_RFC8785,
    }
    report["report_hash"] = profiled_sha256(report, JCS_RFC8785)
    return report


def _relative(path: str | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return Path(path).name


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def format_text(report: dict[str, Any], *, show: tuple[str, ...] = ("error", "warning")) -> str:
    out = [
        f"claim audit of {report['root']} ({report['files_scanned']} files, "
        f"terms from {report['terms_source']})",
        f"  errors: {report['errors']}  warnings: {report['warnings']}  "
        f"waiver debt: {report['waiver_debt']}  "
        + "  ".join(f"{k}: {v}" for k, v in report["counts"].items()),
    ]
    for f in report["findings"]:
        if f["severity"] in show:
            where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            out.append(
                f"  [{f['severity']}] {where}  {f['term']!r} ({f['category']}): {f['text'][:140]}"
            )
    out.append("PASSED" if report["passed"] else "FAILED")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Find claims a repository makes that its evidence doesn't back."
    )
    parser.add_argument("root", type=Path, help="repository to audit")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="claims config (default: governance/claims.json or claims.json under root)",
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="also write the full JSON report here"
    )
    parser.add_argument(
        "--show-info", action="store_true", help="also list denied/backed/waived occurrences"
    )
    parser.add_argument("--require-files", action="store_true", help="refuse an empty scan")
    args = parser.parse_args(argv)
    try:
        report = audit(args.root, args.config)
        if args.require_files and report["files_scanned"] == 0:
            raise Refusal("no tracked text files were scanned")
    except Refusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(
        format_text(
            report, show=("error", "warning", "info") if args.show_info else ("error", "warning")
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
