"""VOID-derived neural capability adapter for Weaver OS."""

from .activation import (
    ActivationAction,
    ActivationEvidence,
    ActivationIntent,
    ActivationRejectCode,
    ActivationStatus,
    BackendActivationResult,
    VoidActivationAdapter,
    build_activation_authority_payload,
)
from .native import NativeVoidBackend, NativeVoidProtocolError

__all__ = [
    "ActivationAction",
    "ActivationEvidence",
    "ActivationIntent",
    "ActivationRejectCode",
    "ActivationStatus",
    "BackendActivationResult",
    "NativeVoidBackend",
    "NativeVoidProtocolError",
    "VoidActivationAdapter",
    "build_activation_authority_payload",
]
