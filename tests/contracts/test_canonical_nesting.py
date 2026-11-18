"""WX-CJSON-1 nesting: the strict reader accepts exactly the depth the encoder can produce.

``canonicalize`` refuses any value nested deeper than ``MAX_DEPTH`` (256). ``parse_strict``
used to have no bound of its own, so it accepted documents ``canonicalize`` could never
have written and, from about 2,000 levels on every supported Python, let the recursive
JSON parser escape as ``RecursionError`` instead of ``CanonicalizationError``. The same
defect was found in every strict reader in the Lumen family review (Lumen Chronicle,
Lumen-Elpis, Lumen-Nexus PG-001R) and in the V008 owner (#134).

Three guards, each tested on its own, because any one of them can hide the removal of
another when the only probe is a very deep payload:

- a non-recursive pre-scan refuses over-deep text before the recursive parser sees it;
- a ``RecursionError`` backstop converts any parser recursion into the normal refusal;
- the tree check refuses a value deeper than ``MAX_DEPTH``, exactly as the encoder does.
"""
from __future__ import annotations

import json

import pytest
from weaver_contracts import canonical
from weaver_contracts.canonical import (
    MAX_DEPTH,
    CanonicalizationError,
    canonicalize,
    is_canonical,
    parse_strict,
)


def arrays(containers: int, leaf: str = "") -> bytes:
    return ("[" * containers + leaf + "]" * containers).encode()


def objects(containers: int, leaf: str = "1") -> bytes:
    return ('{"k":' * containers + leaf + "}" * containers).encode()


def test_the_reader_and_the_writer_share_one_limit():
    assert MAX_DEPTH == 256


def test_exact_boundary_matches_the_encoder_for_empty_innermost_containers():
    # 257 nested empty arrays: the innermost array sits at depth 256, which the encoder
    # accepts. One more puts it at 257, which the encoder refuses.
    deepest = arrays(MAX_DEPTH + 1)
    assert canonicalize(parse_strict(deepest)) == deepest
    with pytest.raises(CanonicalizationError):
        canonicalize(json.loads(arrays(MAX_DEPTH + 2)))
    with pytest.raises(CanonicalizationError, match="nested deeper"):
        parse_strict(arrays(MAX_DEPTH + 2))


def test_exact_boundary_matches_the_encoder_for_a_scalar_leaf():
    # 256 containers around a scalar put the scalar at depth 256: accepted by both.
    # 257 containers put it at 257: refused by both. The pre-scan admits 257 open
    # containers, so this boundary is the tree check's alone.
    for build in (arrays, objects):
        ok = build(MAX_DEPTH, "1")
        assert canonicalize(parse_strict(ok)) == ok
        over = build(MAX_DEPTH + 1, "1")
        with pytest.raises(CanonicalizationError):
            canonicalize(json.loads(over))
        with pytest.raises(CanonicalizationError, match="nested deeper"):
            parse_strict(over)


def test_overdeep_input_never_reaches_the_recursive_parser(monkeypatch):
    # The pre-scan's own job: refuse over-deep text before json.loads runs, so refusal
    # never depends on how much recursion a given interpreter allows.
    calls = []
    real = json.loads

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(canonical.json, "loads", spy)
    with pytest.raises(CanonicalizationError, match="nested deeper"):
        parse_strict(arrays(MAX_DEPTH + 2))
    assert calls == []
    parse_strict(arrays(3))
    assert calls == [1]


def test_a_parser_recursion_error_is_the_ordinary_refusal(monkeypatch):
    # The backstop's own job, on a shallow payload the pre-scan admits.
    real = json.loads
    probe = '{"probe":1}'

    def recursing(text, *args, **kwargs):
        if text == probe:
            raise RecursionError("maximum recursion depth exceeded")
        return real(text, *args, **kwargs)

    monkeypatch.setattr(canonical.json, "loads", recursing)
    with pytest.raises(CanonicalizationError, match="too deep for the parser"):
        parse_strict(probe.encode())


@pytest.mark.parametrize("depth", [2_000, 20_000, 32_000])
def test_very_deep_input_is_refused_cleanly_on_every_interpreter(depth):
    with pytest.raises(CanonicalizationError):
        parse_strict(arrays(depth))
    assert is_canonical(arrays(depth)) is False  # a predicate never raises


def test_structural_characters_inside_strings_do_not_count():
    # One array holding a string of 2,000 brackets and an escaped quote is depth 1.
    shallow = ('["' + "[{" * 1000 + '\\"' + "]}" * 1000 + '"]').encode()
    assert parse_strict(shallow) == ["[{" * 1000 + '"' + "]}" * 1000]


def test_an_escaped_quote_does_not_end_a_string():
    # If \" ended the string, the 300 brackets after it would count as structure.
    text = ('["x\\"' + "[" * 300 + '"]').encode()
    assert parse_strict(text) == ['x"' + "[" * 300]


def test_an_escaped_backslash_does_end_before_the_next_quote():
    # "a\\" is a complete string; the 300 arrays after it are real structure. Treating
    # the second backslash as escaping the quote would hide them inside the string.
    text = ('["a\\\\",' + "[" * 300 + "]" * 300 + "]").encode()
    with pytest.raises(CanonicalizationError, match="nested deeper"):
        parse_strict(text)
