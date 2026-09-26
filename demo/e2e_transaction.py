"""WN-E2E-001: bounded fixture composition; no operational authority."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.boundary_integrity_demo import EpistemicKernelValidator  # noqa: E402
from triadic_controls.ledger import (  # noqa: E402
    GENESIS_PREV_HASH,
    TriadLedger,
    canonical_json,
    compute_event_hash,
)


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def initial_state():
    return {"authority": 0, "artifact": None, "revision": 0}


def transition(state, tx):
    before = digest(state)
    kernel = EpistemicKernelValidator(canonical_head=before)
    verdict, code, layer, delta = kernel.evaluate_transaction(tx)
    after = copy.deepcopy(state)
    # This adapter supports ordinary fixture transactions only, never promotion.
    require(tx["transition_type"] == "ORDINARY", "outside adapter scope")
    require(delta == 0, "unexpected authority movement")
    if verdict == "ACCEPT":
        after["artifact"] = tx["proposal"]["payload_hash"]
        after["revision"] += 1
    receipt = {
        "proposal_sha256": digest(tx),
        "verdict": verdict,
        "code": code,
        "layer": layer,
        "authority_delta": delta,
        "state_before": before,
        "state_after": digest(after),
    }
    require(verdict == "ACCEPT" or before == digest(after), "rejection mutated state")
    return after, receipt


def write_json(path, value):
    path.write_bytes(canonical_json(value) + b"\n")


def source_manifest():
    paths = [
        "demo/e2e_transaction.py",
        "demo/boundary_integrity_demo.py",
        "triadic_controls/ledger.py",
        "schemas/triad_event.schema.json",
        "demo/demo_cases/01_valid_ordinary_proposal.json",
        "demo/demo_cases/02_authority_leak_attempt.json",
    ]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def produce(out):
    out.mkdir(parents=True, exist_ok=False)
    ledger = TriadLedger(out / "chronicle.jsonl")
    state = initial_state()
    receipts = []
    for i, name in enumerate(["01_valid_ordinary_proposal.json", "02_authority_leak_attempt.json"]):
        tx = json.loads((ROOT / "demo/demo_cases" / name).read_text())
        tx["from_state_hash"] = digest(state)
        state, receipt = transition(state, tx)
        require(receipt["verdict"] == ["ACCEPT", "REJECT"][i], "wrong verdict")
        require(
            receipt["code"] == ["SUCCESS_ORDINARY_COMMIT", "AUTHORITY_ERROR"][i],
            "wrong rejection/acceptance reason",
        )
        receipts.append(receipt)
        events = ledger.load_events()
        event = {
            "index": i,
            "timestamp": "2026-09-25T00:00:00Z",
            "event_type": "decided" if i == 0 else "rejected",
            "actor": "WN-E2E-001-synthetic-fixture",
            "public_key": "",
            "payload": {"proposal": tx, "receipt": receipt},
            "prev_hash": events[-1]["event_hash"] if events else GENESIS_PREV_HASH,
            "policy_version": "WN-E2E-001-v0.1",
        }
        event["event_hash"] = compute_event_hash(event)
        ledger.append_event(event)
    write_json(out / "receipts.json", receipts)
    write_json(out / "state.json", state)
    manifest = {
        "protocol": "WN-E2E-001-v0.1",
        "count": 2,
        "tip": ledger.load_events()[-1]["event_hash"],
        "sources": source_manifest(),
        "files": {
            name: hashlib.sha256((out / name).read_bytes()).hexdigest()
            for name in ["receipts.json", "state.json", "chronicle.jsonl"]
        },
    }
    write_json(out / "manifest.json", manifest)


def verify(out):
    manifest = json.loads((out / "manifest.json").read_text())
    require(manifest["sources"] == source_manifest(), "source identity mismatch")
    require(
        set(manifest["files"]) == {"receipts.json", "state.json", "chronicle.jsonl"},
        "wrong file set",
    )
    for name, expected in manifest["files"].items():
        require(
            hashlib.sha256((out / name).read_bytes()).hexdigest() == expected,
            f"file digest mismatch: {name}",
        )
    events = TriadLedger(out / "chronicle.jsonl").load_events()
    require(len(events) == manifest["count"] == 2, "wrong event count")
    require(events[-1]["event_hash"] == manifest["tip"], "checkpoint mismatch")
    state, receipts = initial_state(), []
    for event in events:
        state, receipt = transition(state, event["payload"]["proposal"])
        require(receipt == event["payload"]["receipt"], "semantic replay mismatch")
        receipts.append(receipt)
    require([r["verdict"] for r in receipts] == ["ACCEPT", "REJECT"], "wrong sequence")
    require(receipts[0]["state_before"] != receipts[0]["state_after"], "vacuous accept")
    require(receipts[1]["state_before"] == receipts[1]["state_after"], "state changed")
    require(json.loads((out / "receipts.json").read_text()) == receipts, "receipt mismatch")
    require(json.loads((out / "state.json").read_text()) == state, "state mismatch")
    return {"verdicts": [r["verdict"] for r in receipts], "protected_state": digest(state)}


def child(mode, path):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), mode, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def demonstrate(out):
    produce(out)
    replay = child("verify", out)
    require(replay.returncode == 0, replay.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "fresh"
        result = child("produce", fresh)
        require(result.returncode == 0, result.stderr)
        for name in ("receipts.json", "state.json", "chronicle.jsonl", "manifest.json"):
            require(
                (out / name).read_bytes() == (fresh / name).read_bytes(),
                f"fresh-process inequality: {name}",
            )
    probes = {}
    for name in ("receipts.json", "chronicle.jsonl"):
        path = out / name
        original = path.read_bytes()
        require(b"ACCEPT" in original, "mutation target missing")
        try:
            path.write_bytes(original.replace(b"ACCEPT", b"REJECT", 1))
            result = child("verify", out)
            require(
                result.returncode == 1 and "file digest mismatch" in result.stderr,
                f"tamper survived or verifier crashed: {name}",
            )
            probes[name] = "DETECTED"
        finally:
            path.write_bytes(original)
    summary = {
        "status": "PASS_LOCAL_FIXTURE",
        **verify(out),
        "fresh_process_byte_equality": True,
        "tamper_probes": probes,
        "python": platform.python_version(),
        "authority": "O0_UNCHANGED",
        "independent_reproduction": False,
    }
    write_json(out / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["demo", "produce", "verify"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "demo":
            demonstrate(args.output)
        elif args.mode == "produce":
            produce(args.output)
        else:
            print(json.dumps(verify(args.output), sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
