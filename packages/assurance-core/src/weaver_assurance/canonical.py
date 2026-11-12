"""Canonical data profile used at Weaver authority boundaries."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value is outside the authority-data profile."""


def _validate(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        raise CanonicalizationError(f"floating-point values are forbidden at {path}; use a decimal string")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"object keys must be strings at {path}")
            _validate(item, f"{path}.{key}")
        return
    raise CanonicalizationError(f"unsupported value type {type(value).__name__} at {path}")


def canonical_json(value: Any) -> bytes:
    """Serialize the bounded Weaver JSON profile deterministically.

    Floats are excluded because ordinary JSON does not define one portable
    cross-language representation for every floating-point value.
    """

    _validate(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

