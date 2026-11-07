"""Kernel reducer local implementation boundary.

The reducer behavior covered by the current verification claim is exercised through
the cryptographically bound RC1 witness archive.  No source-tree reducer is claimed
to be implemented by this PR.
"""

IMPLEMENTATION_STATUS = "DEFERRED_TO_BOUND_WITNESS"
WITNESS_ARCHIVE = "releases/weaver-witness-signed-rc1/WEAVER_WITNESS_SIGNED_RC1.zip"

__all__ = ["IMPLEMENTATION_STATUS", "WITNESS_ARCHIVE"]


def __getattr__(name: str):
    if name.startswith("__") and name.endswith("__"):
        # Import machinery and introspection probe dunder names; they must see a
        # normal missing attribute, or the module cannot even be imported.
        raise AttributeError(name)
    raise NotImplementedError(
        f"kernel.reducer.{name} is not implemented in the source tree; "
        "the current verification claim is bound to the RC1 witness archive"
    )
