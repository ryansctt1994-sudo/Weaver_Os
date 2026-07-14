"""Dependency-free local runner for the pytest-style unit functions."""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import test_assurance


def main() -> int:
    failures: list[str] = []
    tests = [
        (name, value)
        for name, value in vars(test_assurance).items()
        if name.startswith("test_") and callable(value)
    ]
    for name, function in sorted(tests):
        try:
            if "tmp_path" in inspect.signature(function).parameters:
                with tempfile.TemporaryDirectory() as directory:
                    function(Path(directory))
            else:
                function()
            print(f"PASS {name}")
        except Exception as exc:  # pragma: no cover - runner reporting
            failures.append(name)
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"RESULT passed={len(tests) - len(failures)} failed={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

