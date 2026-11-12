"""Fail-closed trust-domain checker for the unified layout (UADR-0001).

Each directory directly under ``packages/`` is a trust domain. The checker enforces:

``FORBIDDEN_DOMAIN_IMPORT``
    A domain imports another domain that UADR-0001 does not allow.
``NON_RUNTIME_IMPORT``
    Code under ``packages/`` imports ``research``, ``archive``, ``legacy`` or ``evidence``.
``NON_STDLIB_IMPORT``
    ``contracts`` imports anything outside the Python standard library.
``IO_CAPABLE_IMPORT``
    ``contracts`` or ``verifier`` imports a module that runs processes, opens network
    connections, or writes databases (``sqlite3``, ``subprocess``, ``socket``, ...).
    Verification stays read-only, and effects reach it only through injected objects.
``LEGACY_CANONICALIZER``
    Code under ``packages/`` hashes ``json.dumps(..., sort_keys=True)`` output outside the
    named allowlist. New code uses WX-CJSON-1 (``weaver_contracts.canonical``); see C-CANON-001.
``STALE_ALLOWLIST``
    An allowlisted file no longer contains a legacy canonicalizer, so its entry must go.
``UNKNOWN_DOMAIN`` / ``UNPARSEABLE``
    Fail closed on anything the checker cannot classify.

Until a domain exists, there is nothing to check for it.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED: dict[str, frozenset[str]] = {
    "contracts": frozenset(),
    "runtime": frozenset({"contracts"}),
    "verifier": frozenset({"contracts"}),
    # A witness checks what it signs with the verifier's read-only code and must
    # never reach the operator's runtime (UADR-0001, amended by GD-0005 D14).
    "witness": frozenset({"contracts", "verifier"}),
    "learning": frozenset({"contracts", "runtime"}),
    "release_guard": frozenset({"contracts"}),
    "adapters": frozenset({"contracts"}),
}
NON_RUNTIME_ZONES = frozenset({"research", "archive", "legacy", "evidence"})
STDLIB_ONLY = frozenset({"contracts"})
NO_IO_DOMAINS = frozenset({"contracts", "verifier"})
IO_CAPABLE_MODULES = frozenset(
    {
        "asyncio",
        "ctypes",
        "ftplib",
        "http",
        "imaplib",
        "multiprocessing",
        "poplib",
        "shutil",
        "smtplib",
        "socket",
        "socketserver",
        "sqlite3",
        "subprocess",
        "urllib",
        "xmlrpc",
    }
)
STDLIB = frozenset(sys.stdlib_module_names) | {"__future__"}

# Paths relative to packages/. Each entry names why the legacy canonicalizer stays.
LEGACY_CANONICALIZER_ALLOWLIST: dict[str, str] = {
    "verifier/weaver_verifier/public_log.py": (
        "Rekor hashedrekord SET signature profile: historical signed bytes; not authority JSON"
    ),
    "verifier/weaver_verifier/crypto.py": (
        "C-CANON-001: triadic_controls canonicalize_json; signatures in fixtures depend on it"
    ),
    "verifier/weaver_verifier/claim_transition.py": (
        "C-CANON-001: claim_state_hash moved unchanged in step 4"
    ),
    "verifier/weaver_verifier/pg001r.py": (
        "PG001R-JSON-1: Lumen-Nexus named diagnostic profile, moved verbatim"
    ),
}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    rule: str
    detail: str

    def render(self, root: Path) -> str:
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"{shown}:{self.line}: {self.rule}: {self.detail}"


def _domain_roots(packages_dir: Path) -> dict[str, str]:
    """Map importable top-level module names to the domain that owns them."""
    owners: dict[str, str] = {}
    for domain_dir in sorted(p for p in packages_dir.iterdir() if p.is_dir()):
        owners[f"packages.{domain_dir.name}"] = domain_dir.name
        for child in domain_dir.iterdir():
            if child.is_dir() and (child / "__init__.py").exists():
                owners[child.name] = domain_dir.name
            elif child.suffix == ".py":
                owners[child.stem] = domain_dir.name
    return owners


def _imported_modules(tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                yield node.lineno, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if (
                name in {"import_module", "__import__"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                yield node.lineno, node.args[0].value


def _json_dump_aliases(tree: ast.AST) -> set[str]:
    """Names bound to json.dump/json.dumps by ``from json import ...``."""
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "json" and node.level == 0:
            for alias in node.names:
                if alias.name in {"dump", "dumps"}:
                    aliases.add(alias.asname or alias.name)
    return aliases


def _legacy_canonicalizer_lines(tree: ast.AST) -> list[int]:
    aliases = _json_dump_aliases(tree)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_json_dump = (
            isinstance(func, ast.Attribute)
            and func.attr in {"dump", "dumps"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "json"
        ) or (isinstance(func, ast.Name) and func.id in aliases)
        if not is_json_dump:
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "sort_keys"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
            ):
                lines.append(node.lineno)
    return lines


def _owner(module: str, owners: dict[str, str]) -> str | None:
    parts = module.split(".")
    for size in (2, 1):
        candidate = ".".join(parts[:size])
        if candidate in owners:
            return owners[candidate]
    return None


def _check_file(
    path: Path, domain: str, owners: dict[str, str], relative: str
) -> list[Violation]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        return [Violation(path, 0, "UNPARSEABLE", str(exc))]
    violations: list[Violation] = []
    for line, module in _imported_modules(tree):
        top = module.split(".")[0]
        if top in NON_RUNTIME_ZONES:
            violations.append(
                Violation(path, line, "NON_RUNTIME_IMPORT", f"{domain} imports {module}")
            )
            continue
        target = _owner(module, owners)
        if target is not None:
            if target != domain and target not in ALLOWED[domain]:
                violations.append(
                    Violation(
                        path,
                        line,
                        "FORBIDDEN_DOMAIN_IMPORT",
                        f"{domain} may not import {target} ({module})",
                    )
                )
            continue
        if domain in NO_IO_DOMAINS and top in IO_CAPABLE_MODULES:
            violations.append(
                Violation(path, line, "IO_CAPABLE_IMPORT", f"{domain} imports {module}")
            )
        if domain in STDLIB_ONLY and top not in STDLIB:
            violations.append(
                Violation(path, line, "NON_STDLIB_IMPORT", f"{domain} imports {module}")
            )
    legacy = _legacy_canonicalizer_lines(tree)
    if relative in LEGACY_CANONICALIZER_ALLOWLIST:
        if not legacy:
            violations.append(
                Violation(path, 0, "STALE_ALLOWLIST", "no legacy canonicalizer left; remove entry")
            )
    else:
        violations.extend(
            Violation(
                path,
                line,
                "LEGACY_CANONICALIZER",
                "json.dumps(sort_keys=True); use weaver_contracts.canonical (C-CANON-001)",
            )
            for line in legacy
        )
    return violations


def check(root: Path) -> tuple[list[Violation], int]:
    """Return (violations, number_of_domains_checked)."""
    packages_dir = root / "packages"
    if not packages_dir.is_dir():
        return [], 0
    violations: list[Violation] = []
    owners = _domain_roots(packages_dir)
    domains = sorted(p for p in packages_dir.iterdir() if p.is_dir())
    for domain_dir in domains:
        domain = domain_dir.name
        if domain not in ALLOWED:
            violations.append(
                Violation(domain_dir, 0, "UNKNOWN_DOMAIN", f"'{domain}' is not in UADR-0001")
            )
            continue
        for path in sorted(domain_dir.rglob("*.py")):
            relative = path.relative_to(packages_dir).as_posix()
            violations.extend(_check_file(path, domain, owners, relative))
    return violations, len(domains)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    violations, count = check(args.root)
    for violation in violations:
        print(f"FAIL: {violation.render(args.root)}")
    if violations:
        return 1
    if count == 0:
        print("OK: no trust-domain packages present yet (packages/ absent)")
    else:
        print(f"OK: {count} trust domain(s) checked, no forbidden imports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
