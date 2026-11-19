"""Gate 1 local replay hash-chain controls (not operational witnessing)."""

import json
from pathlib import Path
from typing import Any

from weaver_auth.bedrock.tests.test_all_harnesses import (
    _hash_payload,
    generate_receipt,
    replay_observation,
    replay_verify,
)


def _valid_lines() -> list[str]:
    previous = "GENESIS"
    lines: list[str] = []
    for event in ("ADMIT", "REFUSE"):
        entry: dict[str, Any] = {"prev_hash": previous, "event": event}
        entry["entry_hash"] = _hash_payload(previous, entry)
        previous = entry["entry_hash"]
        lines.append(json.dumps(entry, separators=(",", ":")))
    return lines


def _write(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "chronicle.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_valid_two_entry_chain(tmp_path: Path) -> None:
    assert replay_verify(_write(tmp_path, _valid_lines()))


def test_missing_file_is_not_a_replay_pass(tmp_path: Path) -> None:
    missing = tmp_path / "absent.jsonl"
    assert replay_verify(missing) is False
    assert replay_observation(missing) == ("NOT_ASSESSED", False, None)


def test_empty_file_is_refused(tmp_path: Path) -> None:
    assert not replay_verify(_write(tmp_path, []))


def test_blank_lines_are_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, _valid_lines())
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert not replay_verify(path)


def test_invalid_utf8_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "chronicle.jsonl"
    path.write_bytes(b"\xff")
    assert not replay_verify(path)


def test_malformed_json_is_refused(tmp_path: Path) -> None:
    assert not replay_verify(_write(tmp_path, ['{"prev_hash":']))


def test_non_object_json_is_refused(tmp_path: Path) -> None:
    assert not replay_verify(_write(tmp_path, ['["GENESIS"]']))


def test_duplicate_json_keys_are_refused(tmp_path: Path) -> None:
    line = '{"prev_hash":"GENESIS","prev_hash":"GENESIS","entry_hash":"' + "0" * 64 + '"}'
    assert not replay_verify(_write(tmp_path, [line]))


def test_non_json_nan_is_refused(tmp_path: Path) -> None:
    line = '{"prev_hash":"GENESIS","event":NaN,"entry_hash":"' + "0" * 64 + '"}'
    assert not replay_verify(_write(tmp_path, [line]))


def test_reordered_chain_is_refused(tmp_path: Path) -> None:
    first, second = _valid_lines()
    assert not replay_verify(_write(tmp_path, [second, first]))


def test_missing_genesis_entry_is_refused(tmp_path: Path) -> None:
    assert not replay_verify(_write(tmp_path, _valid_lines()[1:]))


def test_mismatched_previous_hash_is_refused(tmp_path: Path) -> None:
    first, second = _valid_lines()
    item = json.loads(second)
    item["prev_hash"] = "0" * 64
    assert not replay_verify(_write(tmp_path, [first, json.dumps(item)]))


def test_mismatched_entry_hash_is_refused(tmp_path: Path) -> None:
    item = json.loads(_valid_lines()[0])
    item["entry_hash"] = "0" * 64
    assert not replay_verify(_write(tmp_path, [json.dumps(item)]))


def test_truncated_final_entry_is_refused(tmp_path: Path) -> None:
    first, second = _valid_lines()
    assert not replay_verify(_write(tmp_path, [first, second[:-9]]))


def test_oversized_input_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "chronicle.jsonl"
    path.write_bytes(b"x" * 1_000_001)
    assert not replay_verify(path)


def test_receipt_missing_operational_input_is_test_only() -> None:
    receipt = generate_receipt(True, "NOT_ASSESSED", False, None, "a" * 40)
    assert receipt["status"] == "TEST_ONLY_PASS"
    assert receipt["replay_passed"] is False
    assert receipt["replay_status"] == "NOT_ASSESSED"
    assert receipt["qualification"] == "NOT_ASSESSED"
    assert receipt["authority"] == "NONE"
    assert receipt["replay_input_sha256"] is None


def test_receipt_failed_replay_is_failure() -> None:
    receipt = generate_receipt(True, "FAILED", False, "0" * 64, "b" * 40)
    assert receipt["status"] == "FAILURE"


def test_receipt_unbound_source_is_failure() -> None:
    receipt = generate_receipt(True, "NOT_ASSESSED", False, None, "UNAVAILABLE")
    assert receipt["status"] == "FAILURE"
