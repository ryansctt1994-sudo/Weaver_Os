"""Require targeted WeaverActivation TLA+ safety mutations to be detected."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL_DIR = ROOT / "audit-package" / "formal" / "tla+"
MODEL = FORMAL_DIR / "WeaverActivation.tla"
CONFIG = FORMAL_DIR / "WeaverActivation.cfg"

MUTATIONS = (
    (
        "authority-exact-binding",
        "  /\\ c = AuthContract(boundAuthority[r])\n",
        "",
        "Inv_AuthorityExactBinding",
    ),
    (
        "rejection-phase-guard",
        "  /\\ AllowedReject(state[r], code)\n",
        "  /\\ TRUE\n",
        "Inv_RejectionPhaseSound",
    ),
)


def _run_tlc(jar: Path, directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "java",
            "-cp",
            str(jar),
            "tlc2.TLC",
            "-deadlock",
            "-config",
            "WeaverActivation.cfg",
            "WeaverActivation.tla",
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=90,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jar", type=Path)
    args = parser.parse_args()
    jar = args.jar.resolve()

    if not jar.is_file():
        raise SystemExit(f"TLC jar not found: {jar}")

    source = MODEL.read_text()
    config = CONFIG.read_text()

    with tempfile.TemporaryDirectory(prefix="weaver-activation-tla-baseline-") as raw:
        directory = Path(raw)
        (directory / MODEL.name).write_text(source)
        (directory / CONFIG.name).write_text(config)
        baseline = _run_tlc(jar, directory)
    if baseline.returncode != 0:
        print(baseline.stdout + baseline.stderr)
        raise SystemExit("activation TLA mutation baseline failed")

    results: list[dict[str, object]] = []
    for name, old, new, expected_invariant in MUTATIONS:
        if source.count(old) != 1:
            raise SystemExit(f"mutation anchor changed: {name}")

        mutated = source.replace(old, new, 1)
        with tempfile.TemporaryDirectory(prefix=f"weaver-activation-tla-{name}-") as raw:
            directory = Path(raw)
            (directory / MODEL.name).write_text(mutated)
            (directory / CONFIG.name).write_text(config)
            result = _run_tlc(jar, directory)

        combined = result.stdout + result.stderr
        detected = (
            result.returncode != 0
            and expected_invariant in combined
            and "violat" in combined.lower()
        )
        results.append(
            {
                "mutation": name,
                "expected_invariant": expected_invariant,
                "detected": detected,
                "returncode": result.returncode,
            }
        )

    print(
        json.dumps(
            {"schema": "weaver-activation-tla-mutations-1", "results": results},
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if all(bool(item["detected"]) for item in results) else 1)


if __name__ == "__main__":
    main()
