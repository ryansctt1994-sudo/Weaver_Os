"""Named canonical-JSON hash profiles.

The portfolio's repositories hash JSON in three different ways (GAP-013).
Instead of silently changing any of them, which would invalidate hashes
that are already sealed, each way is registered here under a stable profile
id. Anything that stores a hash should also store the profile it was made
with, so the hash stays verifiable after the default moves on.

Profiles
--------
``weaver.c14n.v1``
    ``json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)``.
    What ``receipts.canonical_json`` has always produced. Receipts with
    ``receipt_version == "weaver.authority.receipt.v1"`` use it.

``zorel.ascii.v1``
    The same call with ``ensure_ascii=True`` (non-ASCII escaped as ``\\uXXXX``).
    zorel-kernel's sealed authorship receipt uses it.

``jcs.rfc8785``
    The JSON Canonicalization Scheme, RFC 8785. **The profile for every new
    format.** It is defined independently of Python, so other languages can
    reproduce its bytes. Keys are sorted by UTF-16 code units, and numbers use
    the ECMAScript shortest round-trip form.

For ASCII strings, BMP-only keys and integers, ``weaver.c14n.v1`` and
``jcs.rfc8785`` produce identical bytes. They differ on floats (Python writes
``1e-07`` and ``1.0``; JCS writes ``1e-7`` and ``1``) and on key order when keys
contain characters outside the BMP.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from collections.abc import Callable
from decimal import Decimal
from typing import Any

WEAVER_C14N_V1 = "weaver.c14n.v1"
ZOREL_ASCII_V1 = "zorel.ascii.v1"
JCS_RFC8785 = "jcs.rfc8785"

#: Profile to use for any new hashed format.
DEFAULT_PROFILE = JCS_RFC8785

# Up to this magnitude every integer is exactly representable as a double.
_MAX_SAFE_INT = 2**53 - 1


class CanonicalizationError(ValueError):
    """Raised when a value cannot be canonicalized without losing meaning."""


# --- RFC 8785 ---------------------------------------------------------------


def _jcs_number(value: int | float) -> str:
    if isinstance(value, int):
        if abs(value) <= _MAX_SAFE_INT:
            return str(value)
        # JCS numbers are doubles. A larger integer is accepted only when its
        # decimal text is exactly what JCS prints for the nearest double, so
        # the text, and the value a reader parses, survive unchanged. Anything
        # else (2**53 + 1, 2**64) would come back as a different integer.
        try:
            text = _jcs_number(float(value))
        except OverflowError:
            text = None
        if text != str(value):
            raise CanonicalizationError(
                f"integer {value} would not survive a JCS round-trip; encode it as a string"
            )
        return text
    if not math.isfinite(value):
        raise CanonicalizationError(f"{value!r} is not representable in JSON")
    if value == 0:
        return "0"  # also covers -0.0

    # repr() gives the shortest digit string that round-trips, the same
    # digits ECMAScript picks. Only the layout differs, so re-lay it out
    # with ECMAScript Number::toString rules.
    sign = "-" if value < 0 else ""
    _, digits_tuple, exponent = Decimal(repr(abs(value))).as_tuple()
    if not isinstance(exponent, int):
        raise CanonicalizationError("non-finite decimal exponent")
    digits = "".join(map(str, digits_tuple)).rstrip("0") or "0"
    exponent += len("".join(map(str, digits_tuple))) - len(digits)
    k = len(digits)
    n = exponent + k  # value = 0.digits * 10**n

    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        mantissa = digits if k == 1 else digits[0] + "." + digits[1:]
        body = f"{mantissa}e{'+' if e > 0 else '-'}{abs(e)}"
    return sign + body


def _jcs_string(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("string contains a lone surrogate") from exc
    # With ensure_ascii=False, json.dumps escapes exactly what RFC 8785
    # requires: '"', '\\', the short forms \b \f \n \r \t, and other
    # control characters as lower-case \u00xx. Nothing else is escaped.
    return json.dumps(value, ensure_ascii=False)


def _utf16_key(key: str) -> bytes:
    return key.encode("utf-16-be", "surrogatepass")


def _jcs(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _jcs_number(value)
    if isinstance(value, str):
        return _jcs_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError(f"object key {key!r} is not a string")
        items = sorted(value.items(), key=lambda item: _utf16_key(item[0]))
        return "{" + ",".join(_jcs_string(k) + ":" + _jcs(v) for k, v in items) + "}"
    raise CanonicalizationError(f"type {type(value).__name__} is not JSON")


# --- Registry ---------------------------------------------------------------


def _weaver_v1(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _zorel_ascii_v1(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


PROFILES: dict[str, Callable[[Any], str]] = {
    WEAVER_C14N_V1: _weaver_v1,
    ZOREL_ASCII_V1: _zorel_ascii_v1,
    JCS_RFC8785: _jcs,
}


def canonicalize(value: Any, profile: str = DEFAULT_PROFILE) -> str:
    try:
        serializer = PROFILES[profile]
    except KeyError:
        raise CanonicalizationError(f"unknown hash profile {profile!r}") from None
    return serializer(value)


def profiled_sha256(value: Any, profile: str = DEFAULT_PROFILE) -> str:
    return hashlib.sha256(canonicalize(value, profile).encode("utf-8")).hexdigest()


def verify_profiled_sha256(value: Any, expected: str, profile: str) -> bool:
    """Check a hash under the profile it was declared with. Fails closed."""
    try:
        actual = profiled_sha256(value, profile)
    except (CanonicalizationError, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)
