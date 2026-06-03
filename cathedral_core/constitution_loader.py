"""Minimal loader for Cathedral constitutional invariant YAML.

This loader intentionally supports only the small, explicit YAML subset used by
``constitution/negative_invariants.yaml``.  It avoids adding a runtime YAML
parser dependency for MVP-0 while still making the invariant file testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NegativeInvariant:
    id: str
    statement: str
    severity: str


class InvariantLoadError(ValueError):
    """Raised when the invariant file is malformed."""


def _strip_quoted(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_negative_invariants(path: str | Path) -> list[NegativeInvariant]:
    """Load the constrained negative-invariant YAML format used by MVP-0."""

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    invariants: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    saw_root = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "negative_invariants:":
            saw_root = True
            continue
        if line.startswith("- id:"):
            if current is not None:
                invariants.append(current)
            current = {"id": _strip_quoted(line.split(":", 1)[1])}
            continue
        if current is None:
            raise InvariantLoadError(f"Unexpected invariant content before id: {line}")
        if ":" not in line:
            raise InvariantLoadError(f"Malformed invariant line: {line}")
        key, value = line.split(":", 1)
        current[key.strip()] = _strip_quoted(value)

    if current is not None:
        invariants.append(current)
    if not saw_root:
        raise InvariantLoadError("Missing negative_invariants root")
    if not invariants:
        raise InvariantLoadError("No negative invariants found")

    parsed: list[NegativeInvariant] = []
    for item in invariants:
        missing = {"id", "statement", "severity"} - set(item)
        if missing:
            raise InvariantLoadError(f"Invariant missing required fields: {sorted(missing)}")
        parsed.append(
            NegativeInvariant(
                id=item["id"],
                statement=item["statement"],
                severity=item["severity"],
            )
        )

    return parsed
