from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import verify_attestations
from tools.spine_hash import chain_events

ROOT = Path(__file__).resolve().parents[1]


def load_ledger():
    return json.loads((ROOT / "authority_ledger.json").read_text(encoding="utf-8"))


def load_manifest():
    return json.loads(
        (ROOT / "published_manifest.json").read_text(encoding="utf-8")
    )


def test_known_ledger_hash_and_head():
    ledger_hash, head = chain_events(load_ledger())
    assert ledger_hash == "82713cf5a2d9d294c80ba912d51fc4e29bd460c680686ed2f71f74415addb0c9"
    assert head == "e3ff77f12b8663c1fe1ac14bf1e1bd7d675e969f54e49462f4abcf1f41f97e85"


def test_payload_tamper_changes_hash_and_head():
    ledger = load_ledger()
    clean_hash, clean_head = chain_events(ledger)
    bad = copy.deepcopy(ledger)
    bad[-1]["payload"] += "\nTAMPER"
    bad_hash, bad_head = chain_events(bad)
    assert bad_hash != clean_hash
    assert bad_head != clean_head


def test_manifest_schema_accepts_candidate():
    assert verify_attestations.require_manifest_v12(load_manifest())


def test_manifest_schema_rejects_unknown_field():
    manifest = load_manifest()
    manifest["undeclared"] = True
    with pytest.raises(
        verify_attestations.VerificationError,
        match="MANIFEST_SCHEMA_REJECTED",
    ):
        verify_attestations.require_manifest_v12(manifest)


def test_manifest_schema_rejects_status_value_impersonation():
    manifest = load_manifest()
    manifest["state_digest_status"] = "NOT_COMPUTED"
    with pytest.raises(
        verify_attestations.VerificationError,
        match="MANIFEST_SCHEMA_REJECTED",
    ):
        verify_attestations.require_manifest_v12(manifest)


def test_manifest_hash_is_self_consistent():
    manifest = load_manifest()
    assert (
        verify_attestations.compute_manifest_hash(manifest)
        == manifest["manifest_hash"]
    )


def test_local_spine_scope_passes():
    assert verify_attestations.main(["--scope", "local-spine"]) == 0


def test_e35_scope_is_withheld():
    # A local reducer digest is still not a runtime replay or an independent
    # reproduction result.
    assert verify_attestations.main(["--scope", "e35"]) == 1
