"""Evidence-record path and JSON intake guards.

A passing local hash comparison is only self-consistency, never authenticated
source identity or external witness evidence.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from tools import check_evidence_binding as audit


@pytest.fixture
def record_fixture(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    source = root / "packages" / "runtime" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"INERT_LOCAL_SOURCE\n")
    data = {
        "source": {
            "commit": "a" * 40,
            "tree_clean": True,
            "files_sha256": {
                "packages/runtime/example.py": hashlib.sha256(source.read_bytes()).hexdigest()
            },
        }
    }
    record = root / "evidence.json"
    record.write_text(json.dumps(data), encoding="utf-8")
    return root, source, record, data


def _run(root: Path, record: Path) -> int:
    with (
        patch.object(audit, "ROOT", root),
        patch.object(subprocess, "run", return_value=subprocess.CompletedProcess(["git"], 0, "", "")),
    ):
        return audit.main([str(record)])


def test_valid_bounded_file_matches_without_external_claim(record_fixture, capsys):
    root, _source, record, _data = record_fixture
    assert _run(root, record) == 0
    output = capsys.readouterr().out
    assert "MATCH" in output
    assert "do not prove provenance" in output


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.py",
        "/etc/passwd",
        "packages//runtime/example.py",
        "packages/./runtime/example.py",
        "packages/runtime/../runtime/example.py",
        r"packages\\runtime\\example.py",
    ],
)
def test_noncanonical_source_paths_refused(record_fixture, bad_path, capsys):
    root, _source, record, data = record_fixture
    digest = next(iter(data["source"]["files_sha256"].values()))
    data["source"]["files_sha256"] = {bad_path: digest}
    record.write_text(json.dumps(data))
    assert _run(root, record) == 1
    assert "MATCH" not in capsys.readouterr().out


def test_symlinked_source_outside_checkout_refused(record_fixture, tmp_path, capsys):
    root, source, record, data = record_fixture
    outside = tmp_path / "outside.py"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    record.write_text(json.dumps(data))
    assert _run(root, record) == 1
    assert "MATCH" not in capsys.readouterr().out


def test_symlinked_source_inside_checkout_refused(record_fixture):
    root, source, record, data = record_fixture
    twin = source.parent / "twin.py"
    twin.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(twin)
    record.write_text(json.dumps(data))
    assert _run(root, record) == 1


def test_duplicate_json_source_key_refused_before_file_reads(record_fixture, capsys):
    root, _source, record, data = record_fixture
    original = json.dumps(data)
    modified = original.replace('"tree_clean": true', '"tree_clean": false, "tree_clean": true')
    record.write_text(modified)
    assert _run(root, record) == 1
    assert "duplicate" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_values_rejected(record_fixture, token):
    root, _source, record, data = record_fixture
    raw = json.dumps(data)
    record.write_text(raw.replace('"tree_clean": true', '"tree_clean": ' + token))
    assert _run(root, record) == 1


def test_mutated_source_detected_without_promoting(record_fixture):
    root, source, record, _data = record_fixture
    source.write_bytes(b"CHANGED")
    assert _run(root, record) == 1


def test_malformed_digest_refused(record_fixture):
    root, _source, record, data = record_fixture
    data["source"]["files_sha256"] = {"packages/runtime/example.py": "bad"}
    record.write_text(json.dumps(data))
    assert _run(root, record) == 1


def test_dirty_record_cannot_pass_even_when_file_hash_matches(record_fixture):
    root, _source, record, data = record_fixture
    data["source"]["tree_clean"] = False
    record.write_text(json.dumps(data))
    assert _run(root, record) == 1
