"""Weaver contracts: schemas, canonicalization, and frozen data shapes.

Trust domain ``contracts`` under UADR-0001: imports nothing else in the project.
Defines data rules only; grants no authority and creates no evidence.
"""

from .canonical import PROFILE_ID, CanonicalizationError, canonicalize, parse_strict, sha256_hex

__all__ = ["PROFILE_ID", "CanonicalizationError", "canonicalize", "parse_strict", "sha256_hex"]
