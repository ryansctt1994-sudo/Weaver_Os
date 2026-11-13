"""Regression controls for operator-pinned local replay; fixture pin is NOT a witness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from weaver_auth.bedrock.operator_pinned_replay import main, verify_operator_pin

SOURCE = "a" * 40


def _fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    previous = "GENESIS"
    lines = []
    for event in ("ADMIT", "REFUSE"):
        entry: dict[str, Any] = {"prev_hash": previous, "event": event}
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
        entry["entry_hash"] = hashlib.sha256(previous.encode() + canonical).hexdigest()
        previous = entry["entry_hash"]
        lines.append(json.dumps(entry, sort_keys=True, separators=(",", ":")))
    chronicle = tmp_path / "chronicle.jsonl"
    raw = ("\n".join(lines) + "\n").encode()
    chronicle.write_bytes(raw)
    pin = {
        "schema_version": 1,
        "source_commit": SOURCE,
        "entry_count": 2,
        "terminal_hash": previous,
        "chronicle_sha256": hashlib.sha256(raw).hexdigest(),
    }
    pin_path = tmp_path / "operator-pin.json"
    pin_raw = json.dumps(pin, sort_keys=True, separators=(",", ":")).encode()
    pin_path.write_bytes(pin_raw)
    return chronicle, pin_path, hashlib.sha256(pin_raw).hexdigest()


def _expect_failure(chronicle: Path, pin: Path, digest: str, source: str = SOURCE) -> None:
    with pytest.raises((OSError, ValueError, TypeError, UnicodeError)):
        verify_operator_pin(chronicle, pin, digest, source)


def test_complete_chain_matches_supplied_pin_but_grants_no_authority(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    receipt = verify_operator_pin(log, pin, digest, SOURCE)
    assert receipt["status"] == "PIN_MATCH_LOCAL_CHAIN_PASS"
    assert receipt["scope"] == "PIN_BOUND_LOCAL_REPLAY_ONLY"
    assert receipt["entry_count"] == 2
    assert receipt["independent_pin_custody"] == "NOT_ESTABLISHED_BY_THIS_TOOL"
    assert receipt["independent_witness"] == "NOT_ESTABLISHED"
    assert receipt["operational_authority"] == "NONE"
    assert receipt["evidence_promotion"] == "NONE"


def test_complete_valid_suffix_deletion_is_detected(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    first_line = log.read_text().splitlines()[0]
    log.write_text(first_line + "\n")
    _expect_failure(log, pin, digest)


def test_changed_pin_is_not_authorized_without_external_digest(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    record = json.loads(pin.read_text())
    record["entry_count"] = 1
    pin.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")))
    _expect_failure(log, pin, digest)


@pytest.mark.parametrize("which", ["pin", "chronicle"])
def test_missing_input_refused(tmp_path: Path, which: str) -> None:
    log, pin, digest = _fixture(tmp_path)
    (pin if which == "pin" else log).unlink()
    _expect_failure(log, pin, digest)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("entry_count", True),
        ("entry_count", 0),
        ("entry_count", 3),
        ("terminal_hash", "0" * 64),
        ("chronicle_sha256", "0" * 64),
        ("source_commit", "b" * 40),
        ("schema_version", 2),
    ],
)
def test_pin_field_mutations_refused(tmp_path: Path, field: str, bad_value: Any) -> None:
    log, pin, _ = _fixture(tmp_path)
    record = json.loads(pin.read_text())
    record[field] = bad_value
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    pin.write_bytes(raw)
    _expect_failure(log, pin, hashlib.sha256(raw).hexdigest())


def test_different_operator_expected_source_refused(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    _expect_failure(log, pin, digest, "b" * 40)


def test_wrong_or_invalid_external_digest_refused(tmp_path: Path) -> None:
    log, pin, _ = _fixture(tmp_path)
    for digest in ("", "0" * 64, "x" * 64):
        _expect_failure(log, pin, digest)


def test_recomputed_local_chain_does_not_replace_pinned_chronicle(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    lines = log.read_text().splitlines()
    entry = json.loads(lines[0])
    entry["event"] = "UNAUTHORIZED"
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    entry["entry_hash"] = hashlib.sha256(
        b"GENESIS" + json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    log.write_text(json.dumps(entry) + "\n")
    _expect_failure(log, pin, digest)


@pytest.mark.parametrize("corrupt", ["blank", "duplicate", "nan", "invalid_utf8"])
def test_bad_chronicle_bytes_refused(tmp_path: Path, corrupt: str) -> None:
    log, pin, digest = _fixture(tmp_path)
    if corrupt == "blank":
        log.write_text(log.read_text() + "\n")
    elif corrupt == "duplicate":
        log.write_text('{"prev_hash":"GENESIS","prev_hash":"GENESIS"}\n')
    elif corrupt == "nan":
        log.write_text('{"prev_hash":"GENESIS","event":NaN}\n')
    else:
        log.write_bytes(b"\xff")
    _expect_failure(log, pin, digest)


def test_pin_duplicate_json_member_refused_even_if_digest_matches(tmp_path: Path) -> None:
    log, pin, _ = _fixture(tmp_path)
    raw = pin.read_bytes().rstrip(b"}") + b',"entry_count":2}'
    pin.write_bytes(raw)
    _expect_failure(log, pin, hashlib.sha256(raw).hexdigest())


def test_oversized_chronicle_refused_before_full_read(tmp_path: Path) -> None:
    log, pin, digest = _fixture(tmp_path)
    log.write_bytes(b"x" * 1_000_001)
    _expect_failure(log, pin, digest)


def test_cli_fails_closed_on_absent_evidence(tmp_path: Path, capsys: Any) -> None:
    log, pin, digest = _fixture(tmp_path)
    args = [
        "--chronicle", str(log), "--pin", str(pin),
        "--expected-pin-sha256", digest,
        "--expected-source-commit", SOURCE,
    ]
    assert main(args) == 0
    success = json.loads(capsys.readouterr().out)
    assert success["operational_authority"] == "NONE"
    pin.unlink()
    assert main(args) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure["status"] == "FAILURE"
    assert failure["operational_authority"] == "NONE"
