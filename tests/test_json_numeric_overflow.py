"""Valid JSON exponent syntax must not bypass non-finite intake refusal."""

import pytest

import verify_attestations
from tools.verify_evidence_bundle import BundleRefusal, _json_bytes


@pytest.mark.parametrize("number", ["1e999", "-1e999", "1.8e308"])
def test_attestation_intake_refuses_float_overflow(tmp_path, number):
    path = tmp_path / "overflow.json"
    path.write_text('{"nested":[' + number + "]}", encoding="utf-8")
    with pytest.raises(verify_attestations.VerificationError, match="INVALID_JSON"):
        verify_attestations.load_json(path)


@pytest.mark.parametrize("number", ["1e999", "-1e999", "1.8e308"])
def test_bundle_intake_refuses_float_overflow(number):
    with pytest.raises(BundleRefusal, match="non-finite"):
        _json_bytes(('{"nested":[' + number + "]}").encode(), "fixture")


def test_finite_numeric_intake_is_preserved(tmp_path):
    raw = b'{"values":[1e308,-1.5,0.0,123456789012345678901234567890]}'
    expected = {"values": [1e308, -1.5, 0.0, 123456789012345678901234567890]}
    path = tmp_path / "finite.json"
    path.write_bytes(raw)
    assert verify_attestations.load_json(path) == expected
    assert _json_bytes(raw, "fixture") == expected
