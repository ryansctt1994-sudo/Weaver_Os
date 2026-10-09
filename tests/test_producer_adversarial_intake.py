"""Producer adversarial intake must not accept bytes the bundle verifier refuses."""

import json
from pathlib import Path

from tools.verify_all import load_adversarial_results


def _cases() -> list[dict[str, object]]:
    return [
        {
            "case_id": f"ADV-{index:03d}",
            "status": "PASS",
            "expected_verdict": "REJECT",
            "observed_verdict": "REJECT",
            "exit_code": 1,
            "failure_code": "REJECTED",
        }
        for index in range(1, 7)
    ]


def test_overflow_does_not_yield_passable_results(tmp_path: Path) -> None:
    path = tmp_path / "adversarial-results.json"
    document = {
        "schema": "weaver-adversarial-results-1",
        "elapsed": 1,
        "results": _cases(),
    }
    path.write_text(
        json.dumps(document).replace('"elapsed": 1', '"elapsed": 1e999'),
        encoding="utf-8",
    )
    assert load_adversarial_results(path) == []


def test_duplicate_key_does_not_yield_passable_results(tmp_path: Path) -> None:
    path = tmp_path / "adversarial-results.json"
    body = json.dumps({"schema": "weaver-adversarial-results-1", "results": _cases()})
    path.write_text(body.replace('"schema":', '"schema": "shadow", "schema":', 1), encoding="utf-8")
    assert load_adversarial_results(path) == []


def test_finite_results_still_load(tmp_path: Path) -> None:
    path = tmp_path / "adversarial-results.json"
    cases = _cases()
    path.write_text(
        json.dumps({"schema": "weaver-adversarial-results-1", "elapsed": 1.5, "results": cases}),
        encoding="utf-8",
    )
    assert load_adversarial_results(path) == cases
