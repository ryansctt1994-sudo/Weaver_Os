"""CLAIM-E3-001: reject ambiguous JSON at the existing verifier intake.

Source-pinned to main 50ffc20917e4ca2748f3f647acaec23b3f724855.
This is a RED-first regression fixture, not external evidence.
"""
from __future__ import annotations

import pytest

import verify_attestations


@pytest.mark.parametrize("raw", [
    '{"manifest_version":"1.2","manifest_version":"1.3"}',
    '{"outer":{"authority":"O0","authority":"O1"}}',
    '{"role":"reader","r\\u006fle":"writer"}',
    '{"x":NaN}',
    '{"x":Infinity}',
    '{"x":-Infinity}',
])
def test_verifier_refuses_ambiguous_json(tmp_path, raw):
    subject = tmp_path / "ambiguous.json"
    subject.write_text(raw, encoding="utf-8")
    with pytest.raises(verify_attestations.VerificationError, match="INVALID_JSON"):
        verify_attestations.load_json(subject)


def test_verifier_refuses_invalid_utf8(tmp_path):
    subject = tmp_path / "invalid.json"
    subject.write_bytes(b'{"x":"\xff"}')
    with pytest.raises(verify_attestations.VerificationError, match="INVALID_JSON"):
        verify_attestations.load_json(subject)


def test_verifier_accepts_unique_finite_json(tmp_path):
    subject = tmp_path / "valid.json"
    subject.write_text('{"a":1,"nested":{"b":2}}', encoding="utf-8")
    assert verify_attestations.load_json(subject) == {"a": 1, "nested": {"b": 2}}
