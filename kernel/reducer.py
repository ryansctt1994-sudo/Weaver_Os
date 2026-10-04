"""Kernel reducer local implementation boundary.

The reducer behavior covered by the current verification claim is exercised through
the cryptographically bound RC1 witness archive.  No source-tree reducer is claimed
to be implemented by this PR.
"""

IMPLEMENTATION_STATUS = "DEFERRED_TO_BOUND_WITNESS"
WITNESS_ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"

__all__ = ["IMPLEMENTATION_STATUS", "WITNESS_ARCHIVE"]


def __getattr__(name: str):
    raise NotImplementedError(
        f"kernel.reducer.{name} is not implemented in the source tree; "
        "the current verification claim is bound to the RC1 witness archive"
    )
