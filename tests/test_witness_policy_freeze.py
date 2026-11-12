"""A policy freeze cannot choose between disagreeing declared versions."""

from __future__ import annotations

import json
from pathlib import Path

from tools.witness_policy_freeze import adjudication_record, main


def test_record_withholds_governing_policy() -> None:
    record = adjudication_record()
    assert record["status"] == "DISCREPANCY_UNADJUDICATED"
    assert record["governing_policy"] is None
    assert record["release_target_frozen"] is False
    identities = {item["identity"] for item in record["declared_policies"]}
    assert "e35-reproduction-kit-spec" in identities
    assert "portfolio-e4-pending-witnessed-seal" in identities
    assert "mathos-e4-runnable-computational-support" in identities
    assert len(identities) >= 4


def test_freeze_flag_is_refused(tmp_path: Path, capsys) -> None:
    output = tmp_path / "record.json"
    code = main(["--freeze", "--output", str(output)])
    assert code == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["release_target_frozen"] is False


def test_report_without_freeze_exits_zero(capsys) -> None:
    assert main([]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["governing_policy"] is None
