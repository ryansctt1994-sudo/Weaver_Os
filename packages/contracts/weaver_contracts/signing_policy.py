"""Signing-domain and payload-schema-version allowlist (WVR-010).

A signature covers ``signing_domain`` and ``payload_schema_version``, so a valid signature
proves only that the issuer signed those exact strings. It does not prove the pair is one
this verifier should accept. Without this allowlist, a token an issuer signed for a refusal
context could be presented as an authority token, and a token signed under a retired schema
version could be accepted under the current one.

The rule is fail-closed. A ``(payload_type, signing_domain, payload_schema_version)``
triple is accepted only when it appears in ``SUPPORTED_SIGNING_POLICY``. Adding a domain or
version is a reviewed change to this file, never a configuration value.

This module is pure policy with no state, so it lives in the contracts domain (stdlib only,
UADR-0001).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

UNSUPPORTED_SIGNING_DOMAIN = "UNSUPPORTED_SIGNING_DOMAIN"
UNSUPPORTED_PAYLOAD_SCHEMA_VERSION = "UNSUPPORTED_PAYLOAD_SCHEMA_VERSION"
MALFORMED_ENVELOPE = "MALFORMED_ENVELOPE"

# payload_type -> signing_domain -> the payload_schema_version values accepted with that domain.
# A domain names the version it belongs to, so each domain maps to exactly one version.
SUPPORTED_SIGNING_POLICY: Mapping[str, Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        "AUTHORITY_TOKEN": MappingProxyType(
            {
                "triadic-controls:v0.4.0:authority-token": frozenset({"0.4.0"}),
                "triadic-controls:v0.5.0:authority-token": frozenset({"0.5.0"}),
            }
        ),
        "REFUSAL_SIGNAL": MappingProxyType(
            {
                "triadic-controls:v0.5.0:refusal-signal": frozenset({"0.5.0"}),
            }
        ),
    }
)


def check_signing_policy(
    payload_type: object,
    signing_domain: object,
    payload_schema_version: object,
) -> str | None:
    """Return a stable refusal code, or ``None`` when the triple is allowlisted.

    Missing, non-string, or empty values are malformed. An unknown domain, or a domain
    that is not allowed for this payload type (cross-domain reuse), is
    ``UNSUPPORTED_SIGNING_DOMAIN``. A version not allowed with that domain (unknown
    version, or version confusion) is ``UNSUPPORTED_PAYLOAD_SCHEMA_VERSION``.
    """

    for value in (payload_type, signing_domain, payload_schema_version):
        if not isinstance(value, str) or not value:
            return MALFORMED_ENVELOPE
    domains = SUPPORTED_SIGNING_POLICY.get(payload_type)
    if domains is None:
        return UNSUPPORTED_SIGNING_DOMAIN
    versions = domains.get(signing_domain)
    if versions is None:
        return UNSUPPORTED_SIGNING_DOMAIN
    if payload_schema_version not in versions:
        return UNSUPPORTED_PAYLOAD_SCHEMA_VERSION
    return None
