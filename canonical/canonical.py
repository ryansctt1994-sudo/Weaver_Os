"""Compatibility shim: the canonical JSON profile now lives in the contracts domain.

``canonical.canonical`` was a TODO stub (C-STUB-001). It now re-exports
WX-CJSON-1 from ``weaver_contracts.canonical`` so there is one implementation.
Existing digests made with ``triadic_controls`` or ``tools.spine_hash`` are not
affected; see C-CANON-001.
"""

from weaver_contracts.canonical import (
    MAX_SAFE_INTEGER,
    PROFILE_ID,
    CanonicalizationError,
    canonicalize,
    is_canonical,
    parse_strict,
    sha256_hex,
)

__all__ = [
    "MAX_SAFE_INTEGER",
    "PROFILE_ID",
    "CanonicalizationError",
    "canonicalize",
    "is_canonical",
    "parse_strict",
    "sha256_hex",
]
