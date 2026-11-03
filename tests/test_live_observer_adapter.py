"""Tests for real WEAVER cryptographic verification plus dry-run observer.

Requires source-tree triadic_controls.crypto.verifier: no simulator stand-in.
"""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from benchmarks.agent_reliability import live_adapter
from benchmarks.agent_reliability.live_adapter import (
    FROZEN_V02,
    LiveSession,
    check_observer_response,
    evaluate_live,
    observe_in_subprocess,
)
from benchmarks.agent_reliability.portable import evaluate, make_cases


def _case(family: str = "authorized") -> dict:
    return next(case for case in make_cases() if case["family"] == family)


def _claim(case: dict) -> dict:
    return {key: copy.deepcopy(case["grant"][key]) for key in (
        "principal", "action", "resource", "payload_sha256", "nonce", "expires_at", "epoch")}


def test_frozen_v02_target_unchanged():
    reference = evaluate()
    assert reference["fixture_sha256"] == FROZEN_V02["fixture_sha256"]
    assert reference["report_sha256"] == FROZEN_V02["report_sha256"]
    assert FROZEN_V02["commit"] == "d72737d7fa51704e2af3d222ecc321e4839770c6"


def test_actual_ed25519_grant_then_observed_allow():
    case = _case()
    sess = LiveSession()
    assert sess.issue("grant-1", _claim(case)).valid
    result = sess.attempt("authorized", "grant-1", case["request"])
    assert result["decision"] == "ALLOW"
    observed = observe_in_subprocess([result])
    assert check_observer_response([result], observed)
    assert observed["real_commits"] == 0
    assert observed["records"][0]["would_effect"]["kind"] == "WOULD_WRITE"


def test_invalid_signature_fails_and_would_effect_absent():
    case = _case()
    sess = LiveSession()
    rejected = sess.issue("bad-signature", _claim(case), corrupt_signature=True)
    assert not rejected.valid
    assert "INVALID_SIGNATURE" in rejected.codes
    event = sess.attempt("bad", "bad-signature", case["request"])
    assert event["decision"] == "DENY"
    observed = observe_in_subprocess([event])
    assert observed["records"][0]["would_effect"] is None


def test_signed_refusal_reverses_future_intent_only():
    case = _case()
    sess = LiveSession()
    assert sess.issue("will-revoke", _claim(case)).valid
    assert sess.revoke("will-revoke").valid
    event = sess.attempt("revoked", "will-revoke", case["request"])
    assert event["decision"] == "DENY"
    assert event["reason"] == "grant_revoked"
    assert observe_in_subprocess([event])["records"][0]["would_effect"] is None


def test_bad_refusal_does_not_revoke():
    case = _case()
    sess = LiveSession()
    assert sess.issue("bad-refusal", _claim(case)).valid
    refusal = sess.revoke("bad-refusal", corrupt_signature=True)
    assert not refusal.valid
    assert "INVALID_SIGNATURE" in refusal.codes
    assert sess.attempt("still-valid", "bad-refusal", case["request"])["decision"] == "ALLOW"


def test_no_double_execution_intent():
    case = _case()
    sess = LiveSession()
    assert sess.issue("replay", _claim(case)).valid
    first = sess.attempt("replay", "replay", case["request"])
    second = sess.attempt("replay", "replay", case["request"])
    assert [first["decision"], second["decision"]] == ["ALLOW", "DENY"]
    observed = observe_in_subprocess([first, second])
    assert [bool(e["would_effect"]) for e in observed["records"]] == [True, False]


def test_grant_reuse_rejected_by_real_verifier_replay():
    case = _case()
    sess = LiveSession()
    assert sess.issue("duplicate", _claim(case)).valid
    assert not sess.issue("duplicate", _claim(case)).valid


def test_scope_binding_ends_at_adapter_but_denies_mutations():
    case = _case()
    for key, new_value in (("principal", "wrong"), ("action", "delete"),
                           ("resource", "sandbox/99/not-this"), ("nonce", "different"),
                           ("payload", "evil")):
        sess = LiveSession()
        assert sess.issue("grant", _claim(case)).valid
        attempt = copy.deepcopy(case["request"])
        attempt[key] = new_value
        assert sess.attempt(key, "grant", attempt)["decision"] == "DENY"


def test_expiry_and_stale_epoch_denied_by_adapter():
    for family in ("expired", "revoked"):
        case = _case(family)
        sess = LiveSession()
        assert sess.issue(family, _claim(case)).valid
        assert sess.attempt(family, family, case["request"])["decision"] == "DENY"


def test_no_observation_does_not_create_receipt():
    case = _case()
    sess = LiveSession()
    assert sess.issue("no-evidence", _claim(case)).valid
    event = sess.attempt("no-evidence", "no-evidence", case["request"],
                         evidence_available=False)
    assert event["decision"] == "HALT"
    assert not sess.used


def test_broken_observer_reports_unknown():
    case = _case()
    sess = LiveSession()
    assert sess.issue("observer-down", _claim(case)).valid
    event = sess.attempt("down", "observer-down", case["request"])
    failure = observe_in_subprocess([event], script=Path("/no/such/observer.py"))
    assert failure["observer_classification"] == "UNKNOWN_OBSERVATION"
    assert failure["real_commits"] is None
    assert not check_observer_response([event], failure)


def test_tamper_observer_response_detected():
    case = _case()
    sess = LiveSession()
    assert sess.issue("tamper", _claim(case)).valid
    event = sess.attempt("tamper", "tamper", case["request"])
    output = observe_in_subprocess([event])
    modified = copy.deepcopy(output)
    modified["records"][0]["would_effect"] = None
    assert not check_observer_response([event], modified)


def test_unrelated_sentinel_unchanged(tmp_path: Path):
    sentinel = tmp_path / "protected-sentinel"
    sentinel.write_bytes(b"original-inert-data")
    initial = sentinel.read_bytes()
    case = _case()
    sess = LiveSession()
    assert sess.issue("sentinel", _claim(case)).valid
    event = sess.attempt("sentinel", "sentinel", case["request"])
    observed = observe_in_subprocess([event])
    assert check_observer_response([event], observed)
    assert sentinel.read_bytes() == initial


def test_end_to_end_report_with_exact_reference_cases():
    report = evaluate_live()
    assert report["reference_case_match"]
    assert report["attempts"] == 52
    assert report["allow"] == 8
    assert report["deny"] == 40
    assert report["halt"] == 4
    assert report["observer_records"] == 48
    assert report["unobserved"] == 4
    assert report["actual_commits"] == 0
    assert report["observer_integrity"]
    assert len([x for x in report["grant_events"] if x.get("refusal_verified")]) == 4


def test_observer_requires_exact_classification_and_root_fields():
    case = _case()
    sess = LiveSession()
    assert sess.issue("shape-root", _claim(case)).valid
    event = sess.attempt("shape-root", "shape-root", case["request"])
    good = observe_in_subprocess([event])
    assert check_observer_response([event], good)

    invalid = []
    spoofed = copy.deepcopy(good)
    spoofed["observer_classification"] = "INDEPENDENT_WITNESS"
    invalid.append(spoofed)
    missing = copy.deepcopy(good)
    missing.pop("observer_classification")
    invalid.append(missing)
    extra = copy.deepcopy(good)
    extra["unauthenticated_extra"] = "hidden"
    invalid.append(extra)
    for receipt in invalid:
        assert not check_observer_response([event], receipt)


def test_observer_rejects_malformed_records_without_exception():
    case = _case()
    sess = LiveSession()
    assert sess.issue("shape-record", _claim(case)).valid
    event = sess.attempt("shape-record", "shape-record", case["request"])
    good = observe_in_subprocess([event])
    assert check_observer_response([event], good)

    invalid = []
    not_object = copy.deepcopy(good)
    not_object["records"][0] = "not a record"
    invalid.append(not_object)
    bool_sequence = copy.deepcopy(good)
    bool_sequence["records"][0]["sequence"] = False
    invalid.append(bool_sequence)
    extra_field = copy.deepcopy(good)
    extra_field["records"][0]["shadow"] = "unaccounted"
    invalid.append(extra_field)
    missing_hash = copy.deepcopy(good)
    missing_hash["records"][0].pop("hash")
    invalid.append(missing_hash)
    for receipt in invalid:
        assert not check_observer_response([event], receipt)


def test_malformed_input_decision_fails_closed_without_exception():
    case = _case()
    sess = LiveSession()
    assert sess.issue("malformed-input", _claim(case)).valid
    event = sess.attempt("malformed-input", "malformed-input", case["request"])
    receipt = observe_in_subprocess([event])
    malformed = copy.deepcopy(event)
    malformed["decision"] = ["ALLOW"]  # unhashable, not a decision string

    # A consistent-looking, forged hash chain must not make an invalid event valid.
    forged = copy.deepcopy(receipt)
    record = forged["records"][0]
    record["event"] = malformed
    record["would_effect"] = None
    content = {
        "sequence": 0,
        "prev": "0" * 64,
        "event": malformed,
        "would_effect": None,
        "actual_effect": "NONE",
    }
    record["hash"] = live_adapter.sha(live_adapter.canonical(content))
    forged["head"] = record["hash"]
    assert not check_observer_response([malformed], forged)


@pytest.mark.parametrize("corruption", ["duplicate_head", "float_zero", "nonfinite"])
def test_ambiguous_observer_json_is_unknown_not_a_valid_receipt(
    monkeypatch, corruption: str,
):
    case = _case()
    sess = LiveSession()
    assert sess.issue("duplicate-json", _claim(case)).valid
    event = sess.attempt("duplicate-json", "duplicate-json", case["request"])
    good = observe_in_subprocess([event])
    assert check_observer_response([event], good)

    # Direct semantic check makes float-zero sensitive to the count-type guard
    # even if a separate parser defense would also reject this wire input.
    if corruption == "float_zero":
        for invalid_count in (0.0, False):
            wrong_type = copy.deepcopy(good)
            wrong_type["real_commits"] = invalid_count
            assert not check_observer_response([event], wrong_type)

    encoded = json.dumps(good, sort_keys=True)
    if corruption == "duplicate_head":
        wire = encoded[:-1] + ',"head":' + json.dumps(good["head"]) + "}"
    elif corruption == "float_zero":
        wire = encoded.replace('"real_commits": 0', '"real_commits": 0.0')
    else:
        wire = encoded.replace('"real_commits": 0', '"real_commits": 1e999')
    assert wire != encoded

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["fake-worker"], returncode=0, stdout=wire, stderr=""
        )

    monkeypatch.setattr(live_adapter.subprocess, "run", fake_run)
    result = observe_in_subprocess([event])
    assert result["observer_classification"] == "UNKNOWN_OBSERVATION"
    assert result["real_commits"] is None
    assert not check_observer_response([event], result)
