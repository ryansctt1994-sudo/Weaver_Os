"""Chronicle local implementation boundary.

The executable Chronicle behavior covered by this repository's current verification
claim lives in the cryptographically bound RC1 witness archive.  This source-tree
module is intentionally non-operative until a local implementation is admitted by
its own verification change.

Importing this module is allowed.  Attempting to resolve an implementation symbol
fails loudly rather than silently presenting a TODO stub as working code.
"""

IMPLEMENTATION_STATUS = "DEFERRED_TO_BOUND_WITNESS"
WITNESS_ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"

__all__ = ["IMPLEMENTATION_STATUS", "WITNESS_ARCHIVE"]


def __getattr__(name: str):
    raise NotImplementedError(
        f"chronicle.{name} is not implemented in the source tree; "
        "the current verification claim is bound to the RC1 witness archive"
    )
