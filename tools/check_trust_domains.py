"""Fail-closed trust-domain import checker for the unified layout (UADR-0001).

Each directory directly under ``packages/`` is a trust domain. Python files in a
domain may import only from the domains UADR-0001 allows. Nothing under
``packages/`` may import from the non-runtime zones. An unknown domain
directory is a violation, not something skipped.

Until code moves into ``packages/``, the checker passes and reports that
no domains are present.
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
    "learning": frozenset({"contracts", "runtime"}),
    "release_guard": frozenset({"contracts"}),
    "adapters": frozenset({"contracts"}),
}
NON_RUNTIME_ZONES = frozenset({"research", "archive", "legacy", "evidence"})


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


def _owner(module: str, owners: dict[str, str]) -> str | None:
    parts = module.split(".")
    for size in (2, 1):
        candidate = ".".join(parts[:size])
        if candidate in owners:
            return owners[candidate]
    return None


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
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as exc:
                violations.append(Violation(path, 0, "UNPARSEABLE", str(exc)))
                continue
            for line, module in _imported_modules(tree):
                top = module.split(".")[0]
                if top in NON_RUNTIME_ZONES:
                    violations.append(
                        Violation(path, line, "NON_RUNTIME_IMPORT", f"{domain} imports {module}")
                    )
                    continue
                target = _owner(module, owners)
                if target is None or target == domain:
                    continue
                if target not in ALLOWED[domain]:
                    violations.append(
                        Violation(
                            path,
                            line,
                            "FORBIDDEN_DOMAIN_IMPORT",
                            f"{domain} may not import {target} ({module})",
                        )
                    )
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
