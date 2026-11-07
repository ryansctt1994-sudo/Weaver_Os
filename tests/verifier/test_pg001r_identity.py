"""PG-001R evaluator and conformance suite were moved from Lumen-Nexus with only listed edits.

The edits are import paths, the CLI usage string, and one ``type: ignore`` for this
repository's whole-repo mypy run. None changes test logic.

Reversing exactly these line edits must reproduce the bytes recorded in the Nexus
``evidence/manifests/pg-001r-source-manifest.json``. Any other change breaks this test.
"""

import ast
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

MOVES = {
    "packages/verifier/weaver_verifier/pg001r.py": (
        "9651f32b5c346e5714a13f0e2c5088e5b43b3bbd222f3240e7c709c2c60b2b06",
        [
            (
                "from weaver_contracts.pg001r import (",
                "from packages.contracts.lumen_contracts.pg001r import (",
            ),
            (
                '            "usage: python -m weaver_verifier.pg001r REQUEST.json",',
                '            "usage: python -m '
                'packages.verifier.lumen_verifier.pg001r REQUEST.json",',
            ),
        ],
    ),
    "tests/verifier/test_pg001r_conformance.py": (
        "51a8a5ad1fe336836211c41c09eec2be8a44085c0a777e36674f1f1e776505ae",
        [
            (
                "from weaver_contracts.pg001r import (",
                "from packages.contracts.lumen_contracts.pg001r import (",
            ),
            (
                "from weaver_verifier.pg001r import evaluate",
                "from packages.verifier.lumen_verifier.pg001r import evaluate",
            ),
            (
                # This repository type-checks tests (mypy .); Lumen-Nexus does not.
                "    return replace(base, **overrides)  # type: ignore[arg-type]\n",
                "    return replace(base, **overrides)\n",
            ),
        ],
    ),
}


@pytest.mark.parametrize("path", sorted(MOVES))
def test_only_listed_edits_differ_from_nexus_manifest(path):
    expected_sha256, edits = MOVES[path]
    text = (ROOT / path).read_text(encoding="utf-8")
    for new, old in edits:
        assert text.count(new) == 1, f"edit anchor missing or duplicated: {new!r}"
        text = text.replace(new, old, 1)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == expected_sha256


def test_canonical_suite_has_exactly_19_tests():
    tree = ast.parse((ROOT / "tests/verifier/test_pg001r_conformance.py").read_text())
    names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert len(names) == 19
