"""Adversarial checks for the WN-E2E-001 fixture adapter."""

import hashlib
import json

import pytest

from demo import e2e_transaction as demo
from triadic_controls import ledger


def test_demo_fresh_process_and_tamper(tmp_path):
    demo.demonstrate(tmp_path / "run")


def rebind_file_manifest(out, name):
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["files"][name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    demo.write_json(out / "manifest.json", manifest)


def stale_payload(out):
    path = out / "chronicle.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    # Change a semantically ignored field, retaining stored event hash/tip.
    events[0]["timestamp"] = "2026-09-24T00:00:00Z"
    path.write_bytes(b"".join(ledger.canonical_json(e) + b"\n" for e in events))
    rebind_file_manifest(out, "chronicle.jsonl")


def test_stale_payload_rejected_by_ledger_even_if_file_hash_rebound(tmp_path):
    out = tmp_path / "run"
    demo.produce(out)
    stale_payload(out)
    with pytest.raises(ledger.LedgerValidationError, match="event_hash mismatch"):
        demo.verify(out)


def test_hash_gate_removal_mutant_is_exposed(tmp_path, monkeypatch):
    out = tmp_path / "run"
    demo.produce(out)
    stale_payload(out)
    # Test the existing ledger gate directly: removing it admits stale payloads.
    # This is a deliberate mutant, not evidence of an unpatched production defect.
    monkeypatch.setattr(ledger, "verify_event_hash", lambda event: None)
    assert len(ledger.TriadLedger(out / "chronicle.jsonl").load_events()) == 2


def test_rejection_mutation_is_caught(tmp_path, monkeypatch):
    original = demo.transition

    def mutant(state, tx):
        after, receipt = original(state, tx)
        if receipt["verdict"] == "REJECT":
            after["authority"] += 1
            receipt["state_after"] = demo.digest(after)
        return after, receipt

    monkeypatch.setattr(demo, "transition", mutant)
    out = tmp_path / "run"
    demo.produce(out)
    with pytest.raises(ValueError, match="state changed"):
        demo.verify(out)


@pytest.mark.parametrize("mode", ["empty", "truncate", "reorder"])
def test_structural_corruption_rejected(tmp_path, mode):
    out = tmp_path / "run"
    demo.produce(out)
    path = out / "chronicle.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(
        {"empty": b"", "truncate": lines[0], "reorder": b"".join(reversed(lines))}[mode]
    )
    rebind_file_manifest(out, "chronicle.jsonl")
    with pytest.raises(ValueError):
        demo.verify(out)


def test_receipt_rewrite_rejected_after_file_hash_rebound(tmp_path):
    out = tmp_path / "run"
    demo.produce(out)
    receipts = json.loads((out / "receipts.json").read_text())
    receipts[1]["verdict"] = "ACCEPT"
    demo.write_json(out / "receipts.json", receipts)
    rebind_file_manifest(out, "receipts.json")
    with pytest.raises(ValueError, match="receipt mismatch"):
        demo.verify(out)
