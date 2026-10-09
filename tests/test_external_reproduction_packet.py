"""The external packet may describe local bytes, never a witness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.emit_external_reproduction_packet import (
    PINNED_HEAD,
    SOURCE_FILES,
    build_packet,
    main,
)

ZERO = "e2232fcb2bb70e1535c43750429baa719fed815b"


def _seed(root: Path) -> None:
    for relative in SOURCE_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture:{relative}\n", encoding="utf-8")


def test_packet_binds_local_bytes_and_withholds_trust(tmp_path: Path) -> None:
    _seed(tmp_path)
    packet = build_packet(tmp_path, PINNED_HEAD)

    assert packet["authenticated_attestation"] is False
    assert packet["witness_claimed"] is False
    assert packet["authority"]["evidence_ceiling"] == "E2"
    assert packet["authority"]["witness"] == "W0"
    assert packet["authority"]["promotion"] == "WITHHELD"
    assert packet["source_identities"]["pinned_head_match"] is True
    assert packet["packet_complete"] is True
    assert packet["ruleset_enforcement"] == "NOT_ESTABLISHED"
    assert packet["witness_policy_adjudication"] == "WITHHELD"
    assert len(packet["source_files"]) == len(SOURCE_FILES)
    assert all(item["status"] == "UNAUTHENTICATED_CLAIM" for item in packet["hosted_run_claims"])
    assert "independently_authenticated_witness" in packet["missing_trust_anchors"]


def test_unpinned_head_is_recorded_not_promoted(tmp_path: Path) -> None:
    _seed(tmp_path)
    packet = build_packet(tmp_path, "a" * 40)
    assert packet["source_identities"]["pinned_head_match"] is False
    assert packet["authenticated_attestation"] is False


def test_missing_source_file_is_incomplete(tmp_path: Path) -> None:
    packet = build_packet(tmp_path, PINNED_HEAD)
    assert packet["packet_complete"] is False
    assert set(packet["missing_source_files"]) == set(SOURCE_FILES)


def test_claim_witness_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed(tmp_path)
    code = main(["--root", str(tmp_path), "--claim-witness", "--observed-head", ZERO])
    assert code == 2
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert captured.out == ""


def test_require_pinned_head_rejects_other_commit(tmp_path: Path) -> None:
    _seed(tmp_path)
    code = main(
        [
            "--root",
            str(tmp_path),
            "--observed-head",
            "b" * 40,
            "--require-pinned-head",
        ]
    )
    assert code == 1


def test_cli_writes_packet(tmp_path: Path) -> None:
    _seed(tmp_path)
    output = tmp_path / "packet.json"
    code = main(
        [
            "--root",
            str(tmp_path),
            "--observed-head",
            PINNED_HEAD,
            "--require-pinned-head",
            "--output",
            str(output),
        ]
    )
    assert code == 0
    packet = json.loads(output.read_text(encoding="utf-8"))
    assert packet["packet_version"] == "external-reproduction-packet-v1"
    assert packet["scope"] == "LOCAL_BYTES_ONLY_NO_AUTHENTICATED_ATTESTATION"
