"""Gate 1 negative controls: absent/empty replay evidence must never pass.

These tests use temporary local files only and do not run the full Gate 1 harness.
"""

import json

from test_all_harnesses import _hash_payload, generate_receipt, replay_verify


def test_missing_chronicle_fails_closed(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert not replay_verify(missing)
    receipt = generate_receipt(tests_passed=True, replay_passed=replay_verify(missing))
    assert receipt["status"] == "FAILURE"


def test_empty_and_whitespace_chronicle_fail_closed(tmp_path):
    for data in ("", "  \n\t\n"):
        empty = tmp_path / "empty.jsonl"
        empty.write_text(data, encoding="utf-8")
        assert not replay_verify(empty)


def test_corrupted_chronicle_is_refused(tmp_path):
    file = tmp_path / "corrupted.jsonl"
    file.write_text('{"prev_hash":"WRONG","entry_hash":"NOT_VALID"}\n', encoding="utf-8")
    assert not replay_verify(file)


def test_valid_single_entry_chronicle_still_passes(tmp_path):
    entry = {"prev_hash": "GENESIS", "event_type": "TEST", "payload": {"n": 1}}
    entry["entry_hash"] = _hash_payload("GENESIS", entry)
    file = tmp_path / "valid.jsonl"
    file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    assert replay_verify(file)
