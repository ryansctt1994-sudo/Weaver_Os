import hashlib
import json
from pathlib import Path

import pytest
import rfc8785
from weaver_contracts.canonical import (
    MAX_SAFE_INTEGER,
    PROFILE_ID,
    CanonicalizationError,
    canonicalize,
    is_canonical,
    parse_strict,
    sha256_hex,
)

from tools.mathos_bench.mathos_bench_v0_1 import canonical_json as mathos_canonical
from tools.spine_hash import canonical as spine_canonical
from triadic_controls.crypto.verifier import canonicalize_json as triadic_canonicalize

VECTORS_PATH = (
    Path(__file__).resolve().parents[2]
    / "packages/contracts/weaver_contracts/vectors/wx_cjson_1.json"
)
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
VALID = VECTORS["valid"]
REJECT = VECTORS["reject"]


def test_vector_file_is_for_this_profile():
    assert VECTORS["profile"] == PROFILE_ID
    assert len(VALID) == 19
    assert len(REJECT) == 14
    assert len({v["id"] for v in VALID + REJECT}) == len(VALID) + len(REJECT)


@pytest.mark.parametrize("vector", VALID, ids=[v["id"] for v in VALID])
def test_valid_vector_matches_reference(vector):
    value = parse_strict(vector["input"].encode("utf-8"))
    out = canonicalize(value)
    assert out.decode("utf-8") == vector["canonical"]
    assert hashlib.sha256(out).hexdigest() == vector["sha256"]
    assert sha256_hex(value) == vector["sha256"]
    assert is_canonical(out)


@pytest.mark.parametrize("vector", VALID, ids=[v["id"] for v in VALID])
def test_independent_rfc8785_implementation_agrees(vector):
    value = parse_strict(vector["input"].encode("utf-8"))
    assert rfc8785.dumps(value) == vector["canonical"].encode("utf-8")


@pytest.mark.parametrize("vector", REJECT, ids=[v["id"] for v in REJECT])
def test_reject_vector_is_rejected(vector):
    with pytest.raises(CanonicalizationError) as info:
        parse_strict(bytes.fromhex(vector["input_hex"]))
    assert vector["reason_contains"].lower() in str(info.value).lower()


@pytest.mark.parametrize(
    "name, fn",
    [
        ("triadic_controls.canonicalize_json", triadic_canonicalize),
        ("tools.spine_hash.canonical", spine_canonical),
        (
            "tools.mathos_bench.mathos_bench_v0_1.canonical_json",
            lambda value: mathos_canonical(value).encode("utf-8"),
        ),
    ],
)
def test_legacy_canonicalizer_divergence_is_pinned(name, fn):
    """C-CANON-001: legacy canonicalizers differ from WX-CJSON-1 on known vectors.

    The set is pinned so a change in either direction is visible in review.
    """
    diverging = []
    for vector in VALID:
        value = parse_strict(vector["input"].encode("utf-8"))
        if fn(value) != vector["canonical"].encode("utf-8"):
            diverging.append(vector["id"])
    assert diverging == VECTORS["divergence"][name]


def test_triadic_divergence_is_key_order_only():
    assert VECTORS["divergence"]["triadic_controls.canonicalize_json"] == ["V12-key-order-utf16"]


@pytest.mark.parametrize(
    "value",
    [1.0, float("nan"), MAX_SAFE_INTEGER + 1, -(MAX_SAFE_INTEGER + 1), {1: "x"}, b"x", {"a": {1}}],
)
def test_canonicalize_rejects_out_of_profile_values(value):
    with pytest.raises(CanonicalizationError):
        canonicalize(value)


def test_canonicalize_rejects_lone_surrogate_in_python_string():
    with pytest.raises(CanonicalizationError):
        canonicalize("\ud800")


def test_canonicalize_rejects_excessive_nesting():
    value: list = []
    for _ in range(300):
        value = [value]
    with pytest.raises(CanonicalizationError):
        canonicalize(value)


def test_bool_is_not_treated_as_int():
    assert canonicalize([True, 1]) == b"[true,1]"


def test_tuple_is_an_array():
    assert canonicalize({"a": (1, 2)}) == b'{"a":[1,2]}'


def test_non_canonical_bytes_are_reported():
    assert not is_canonical(b'{"b":1,"a":2}')
    assert not is_canonical(b"1.5")
    assert is_canonical(b'{"a":2,"b":1}')


def test_parse_strict_requires_bytes():
    with pytest.raises(CanonicalizationError):
        parse_strict('{"a":1}')  # type: ignore[arg-type]
