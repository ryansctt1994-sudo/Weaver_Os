"""Receipt verifier local implementation boundary.

Receipt behavior in the current verification claim is exercised through the
cryptographically bound RC1 witness archive.  The lightweight JSON Schema remains
available under ``schemas/triad_receipt.schema.json`` for structural validation,
but this module does not claim a local cryptographic receipt verifier yet.
"""

IMPLEMENTATION_STATUS = "DEFERRED_TO_BOUND_WITNESS"
WITNESS_ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"

__all__ = ["IMPLEMENTATION_STATUS", "WITNESS_ARCHIVE"]


def __getattr__(name: str):
    raise NotImplementedError(
        f"receipt.verify.{name} is not implemented in the source tree; "
        "the current verification claim is bound to the RC1 witness archive"
    )
