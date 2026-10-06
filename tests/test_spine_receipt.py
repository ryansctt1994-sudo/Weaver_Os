from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.emit_spine_receipt import build_receipt

ROOT = Path(__file__).resolve().parents[1]


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_local_receipt_is_bounded_and_passes():
    receipt = build_receipt(
        load_json("published_manifest.json"),
        load_json("authority_ledger.json"),
        verified_commit="a" * 40,
        source_head_sha="a" * 40,
        environ={},
    )

    assert receipt["overall_result"] == "PASS"
    assert receipt["verified_commit"] == "a" * 40
    assert receipt["source_head_sha"] == "a" * 40
    assert receipt["execution_class"] == "LOCAL_OPERATOR_EXECUTION"
    assert receipt["operator_independence"] == "NOT_ESTABLISHED"
    assert receipt["witness_state"] == "W0"
    assert receipt["operational_authority"] == "O0_WITHHELD"
    assert receipt["production"] == "PROHIBITED"
    assert receipt["derived"]["chain_head"] == (
        "e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85"
    )
    assert receipt["derived"]["local_state_digest"] == (
        "39a5996b1bba7a0ed4f0a5c549ad58af5300b5abb5890ddf9eb47c9d039c5a0e"
    )
    assert len(receipt["receipt_sha256"]) == 64


def test_ci_receipt_distinguishes_verified_merge_from_source_head():
    receipt = build_receipt(
        load_json("published_manifest.json"),
        load_json("authority_ledger.json"),
        verified_commit="c" * 40,
        source_head_sha="b" * 40,
        environ={
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "pull_request",
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
        },
    )

    assert receipt["verified_commit"] == "c" * 40
    assert receipt["source_head_sha"] == "b" * 40
    assert receipt["execution_class"] == "REMOTE_CI_SAME_ORIGIN"
    assert receipt["operator_independence"] == "NOT_ESTABLISHED"
    assert receipt["witness_state"] == "W0"


def test_manifest_substitution_makes_receipt_fail():
    manifest = copy.deepcopy(load_json("published_manifest.json"))
    manifest["expected_head_hash"] = "0" * 64

    receipt = build_receipt(
        manifest,
        load_json("authority_ledger.json"),
        verified_commit="c" * 40,
        source_head_sha="c" * 40,
        environ={},
    )

    assert receipt["overall_result"] == "FAIL"
    assert receipt["checks"]["chain_head"] is False
    assert receipt["checks"]["manifest_hash"] is False
