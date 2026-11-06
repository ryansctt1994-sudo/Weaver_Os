import hashlib
import json
from pathlib import Path
from urllib.error import URLError

import pytest
from cryptography.exceptions import InvalidSignature

from triadic_controls.crypto import live_log

FIXTURE = (
    Path(__file__).resolve().parents[2] / "evidence/silicon/2026-11-06/gate-discrimination/live-log"
)


def test_real_service_checkpoint_and_consistency_proof():
    report = json.loads((FIXTURE / "report.json").read_text())
    live = json.loads((FIXTURE / "live-log.json").read_text())
    proof = json.loads((FIXTURE / "consistency-proof.json").read_text())["hashes"]
    key = (FIXTURE / "service-public-key.pem").read_bytes()
    assert live_log.verify_checkpoint(live["signedTreeHead"], key) == (
        report["tree_id"],
        report["live_tree_size"],
        report["live_root"],
    )
    live_log.verify_consistency(
        report["bundled_tree_size"],
        report["live_tree_size"],
        report["bundled_root"],
        report["live_root"],
        proof,
    )
    altered = list(proof)
    altered[0] = "0" * 64
    with pytest.raises(ValueError):
        live_log.verify_consistency(
            report["bundled_tree_size"],
            report["live_tree_size"],
            report["bundled_root"],
            report["live_root"],
            altered,
        )
    with pytest.raises((ValueError, InvalidSignature)):
        live_log.verify_checkpoint(
            live["signedTreeHead"].replace(
                str(report["live_tree_size"]), str(report["live_tree_size"] + 1)
            ),
            key,
        )


def root(leaves):
    if len(leaves) == 1:
        return leaves[0]
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    return hashlib.sha256(b"\x01" + root(leaves[:split]) + root(leaves[split:])).digest()


def subproof(m, leaves, known=True):
    if m == len(leaves):
        return [] if known else [root(leaves)]
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    if m <= split:
        return subproof(m, leaves[:split], known) + [root(leaves[split:])]
    return subproof(m - split, leaves[split:], False) + [root(leaves[:split])]


def test_all_small_tree_boundaries():
    leaves = [hashlib.sha256(b"\x00" + bytes([i])).digest() for i in range(24)]
    for size in range(1, 25):
        for prior in range(1, size + 1):
            proof = [h.hex() for h in subproof(prior, leaves[:size])]
            live_log.verify_consistency(
                prior, size, root(leaves[:prior]).hex(), root(leaves[:size]).hex(), proof
            )
            with pytest.raises(ValueError):
                live_log.verify_consistency(
                    prior, size, root(leaves[:prior]).hex(), "0" * 64, proof
                )


def test_network_failure_is_inconclusive(tmp_path, monkeypatch):
    manifest = tmp_path / "checkpoint.json"
    manifest.write_bytes(b"{}")

    def fail(*args, **kwargs):
        raise URLError("synthetic outage")

    monkeypatch.setattr(live_log.urllib.request, "urlopen", fail)
    result = live_log.audit(
        manifest, tmp_path / "entry.json", hashlib.sha256(b"{}").hexdigest(), tmp_path / "attempt"
    )
    assert result["status"] == "INCONCLUSIVE"
    assert result["reason_codes"] == ["LIVE_LOG_CHECK_FAILED"]
    assert result["production_authority_earned"] is False
