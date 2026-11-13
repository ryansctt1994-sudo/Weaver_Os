"""WX-CJSON-1: the canonical JSON profile for authority-bearing data.

WX-CJSON-1 is RFC 8785 (JSON Canonicalization Scheme) restricted so that every
conforming implementation produces the same bytes without needing to agree on
floating-point formatting:

- values are objects with string keys, arrays, strings, integers, ``true``,
  ``false`` and ``null``;
- floats are rejected, and so are integers outside the I-JSON safe range
  ``[-(2**53 - 1), 2**53 - 1]``;
- strings must be valid Unicode (no lone surrogates);
- object keys are sorted by UTF-16 code units and strings are escaped exactly as
  RFC 8785 specifies.

``parse_strict`` is the matching reader. It rejects duplicate keys, floats and
exponents, ``NaN``/``Infinity``, a byte-order mark, invalid UTF-8, lone surrogate
escapes, and any value nested deeper than ``MAX_DEPTH``: it accepts exactly the
nesting the encoder can produce. Over-deep text is refused before the recursive JSON
parser sees it, so refusal never depends on an interpreter's recursion limit.

This module defines data rules only. It grants no authority and creates no
evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

PROFILE_ID = "WX-CJSON-1"
MAX_SAFE_INTEGER = 2**53 - 1
# The deepest a value may sit: the top-level value is depth 0, its members depth 1, and
# so on. The encoder and the strict reader share this one limit.
MAX_DEPTH = 256

_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class CanonicalizationError(ValueError):
    """Raised when a value or document is outside the WX-CJSON-1 profile."""


def _check_string(value: str) -> None:
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise CanonicalizationError("strings must not contain lone surrogates")


def _encode_string(value: str) -> str:
    _check_string(value)
    out = ['"']
    for char in value:
        escaped = _ESCAPES.get(char)
        if escaped is not None:
            out.append(escaped)
        elif ord(char) < 0x20:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _utf16_key(key: str) -> bytes:
    return key.encode("utf-16-be")


def _encode(value: Any, depth: int) -> str:
    if depth > MAX_DEPTH:
        raise CanonicalizationError(f"nesting deeper than {MAX_DEPTH} levels")
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalizationError(f"integer outside the I-JSON safe range: {value}")
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError("floats are not allowed in WX-CJSON-1")
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, Mapping):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("object keys must be strings")
        items = sorted(value.items(), key=lambda item: _utf16_key(item[0]))
        body = ",".join(f"{_encode_string(k)}:{_encode(v, depth + 1)}" for k, v in items)
        return "{" + body + "}"
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return "[" + ",".join(_encode(item, depth + 1) for item in value) + "]"
    raise CanonicalizationError(f"unsupported type: {type(value).__name__}")


def canonicalize(value: Any) -> bytes:
    """Return the WX-CJSON-1 canonical UTF-8 bytes for ``value``."""
    return _encode(value, 0).encode("utf-8")


def sha256_hex(value: Any) -> str:
    """SHA-256 hex digest of the canonical bytes of ``value``."""
    return hashlib.sha256(canonicalize(value)).hexdigest()


def _reject_float(text: str) -> Any:
    raise CanonicalizationError(f"floats and exponents are not allowed: {text}")


def _reject_constant(text: str) -> Any:
    raise CanonicalizationError(f"non-finite constants are not allowed: {text}")


def _bounded_int(text: str) -> int:
    value = int(text)
    if abs(value) > MAX_SAFE_INTEGER:
        raise CanonicalizationError(f"integer outside the I-JSON safe range: {text}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CanonicalizationError(f"duplicate object key: {key!r}")
        out[key] = value
    return out


def _check_nesting(text: str) -> None:
    """Refuse text nested past what the encoder can produce, without recursing.

    Counts ``[`` and ``{`` that open outside string literals, with backslash escapes
    handled so structural characters inside a string never count. The deepest container
    the encoder can emit is an empty one at depth ``MAX_DEPTH``, the ``MAX_DEPTH + 1``-th
    open container; one more is refused here, before the recursive parser runs.
    """
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH + 1:
                raise CanonicalizationError(f"nested deeper than {MAX_DEPTH} levels")
        elif char in "]}":
            depth -= 1


def _check_tree(value: Any, depth: int = 0) -> None:
    # The same rule the encoder applies: no value deeper than MAX_DEPTH.
    if depth > MAX_DEPTH:
        raise CanonicalizationError(f"value nested deeper than {MAX_DEPTH} levels")
    if isinstance(value, str):
        _check_string(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_string(key)
            _check_tree(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_tree(item, depth + 1)


def parse_strict(data: bytes) -> Any:
    """Parse JSON bytes, rejecting anything outside WX-CJSON-1."""
    if not isinstance(data, (bytes, bytearray)):
        raise CanonicalizationError("parse_strict takes bytes")
    if data.startswith(b"\xef\xbb\xbf"):
        raise CanonicalizationError("byte-order mark is not allowed")
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalizationError("input is not valid UTF-8") from exc
    _check_nesting(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_float=_reject_float,
            parse_int=_bounded_int,
            parse_constant=_reject_constant,
        )
    except RecursionError as exc:  # backstop: recursion the pre-scan did not prevent
        raise CanonicalizationError("JSON nesting is too deep for the parser") from exc
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(f"invalid JSON: {exc.msg}") from exc
    _check_tree(value)
    return value


def is_canonical(data: bytes) -> bool:
    """True when ``data`` parses under WX-CJSON-1 and is already in canonical form."""
    try:
        return canonicalize(parse_strict(data)) == bytes(data)
    except CanonicalizationError:
        return False
