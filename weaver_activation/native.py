"""Native C ABI seam for the Weaver Activation Runtime."""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .activation import CONTRACT_VERSION, ActivationIntent, BackendActivationResult

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DEFAULT_SYMBOL = "weaver_activate_v1"
_DEFAULT_MAX_RESPONSE_BYTES = 64 * 1024


class NativeWeaverProtocolError(RuntimeError):
    """Raised when the native activation boundary fails closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metric(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativeWeaverProtocolError(f"{name} must be a finite number or null")
    number = float(value)
    if not math.isfinite(number):
        raise NativeWeaverProtocolError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class NativeWeaverBackend:
    """Callable adapter for the frozen Weaver activation ABI v1."""

    library_path: Path
    input_bytes: bytes
    symbol: str = _DEFAULT_SYMBOL
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        object.__setattr__(self, "library_path", Path(self.library_path))
        object.__setattr__(self, "input_bytes", bytes(self.input_bytes))
        if not _SYMBOL_RE.fullmatch(self.symbol):
            raise ValueError("native symbol must be a C identifier")
        if self.max_response_bytes < 1024 or self.max_response_bytes > 8 * 1024 * 1024:
            raise ValueError("max_response_bytes must be between 1 KiB and 8 MiB")

    def __call__(self, intent: ActivationIntent) -> BackendActivationResult:
        if intent.contract_version != CONTRACT_VERSION:
            raise NativeWeaverProtocolError("unsupported activation contract version")
        if intent.backend_sha256 is None or not _SHA256_RE.fullmatch(intent.backend_sha256):
            raise NativeWeaverProtocolError("native activation requires backend_sha256 binding")
        if not self.library_path.is_file():
            raise NativeWeaverProtocolError("native backend library is unavailable")

        library_digest_before = _sha256_file(self.library_path)
        if library_digest_before != intent.backend_sha256:
            raise NativeWeaverProtocolError(
                "native backend digest does not match signed contract"
            )

        input_digest = hashlib.sha256(self.input_bytes).hexdigest()
        if input_digest != intent.input_sha256:
            raise NativeWeaverProtocolError("input bytes do not match signed contract")

        try:
            library = ctypes.CDLL(str(self.library_path))
            entry = getattr(library, self.symbol)
        except (OSError, AttributeError) as exc:
            raise NativeWeaverProtocolError("native activation entry point unavailable") from exc

        library_digest_loaded = _sha256_file(self.library_path)
        if library_digest_loaded != library_digest_before:
            raise NativeWeaverProtocolError("native backend changed during admission")

        request = {
            "contract_version": intent.contract_version,
            "contract_sha256": intent.contract_sha256(),
            "request_id": intent.request_id,
            "model_id": intent.model_id,
            "backend_id": intent.backend_id,
            "backend_sha256": intent.backend_sha256,
            "action": intent.action.value,
            "checkpoint_sha256": intent.checkpoint_sha256,
            "input_sha256": intent.input_sha256,
            "retention_floor": intent.retention_floor,
        }
        request_bytes = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        input_buffer = (ctypes.c_ubyte * len(self.input_bytes)).from_buffer_copy(
            self.input_bytes
        )
        response_buffer = ctypes.create_string_buffer(self.max_response_bytes)
        response_length = ctypes.c_size_t(0)
        request_buffer = ctypes.create_string_buffer(request_bytes)

        entry.argtypes = [
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        entry.restype = ctypes.c_int

        code = entry(
            request_buffer,
            len(request_bytes),
            input_buffer,
            len(self.input_bytes),
            response_buffer,
            self.max_response_bytes,
            ctypes.byref(response_length),
        )
        if code != 0:
            raise NativeWeaverProtocolError(f"native backend returned status {code}")
        if response_length.value == 0 or response_length.value > self.max_response_bytes:
            raise NativeWeaverProtocolError("native backend returned invalid response length")

        library_digest_after = _sha256_file(self.library_path)
        if library_digest_after != library_digest_before:
            raise NativeWeaverProtocolError("native backend changed during execution")

        raw = response_buffer.raw[: response_length.value]
        try:
            document = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NativeWeaverProtocolError("native backend returned invalid JSON") from exc
        if not isinstance(document, dict):
            raise NativeWeaverProtocolError("native response must be a JSON object")

        required = {
            "contract_version",
            "request_id",
            "model_id",
            "backend_id",
            "checkpoint_sha256",
            "output_sha256",
        }
        allowed = required | {"primary_metric", "retention_metric"}
        if set(document) - allowed:
            raise NativeWeaverProtocolError("native response contains unknown fields")
        if not required.issubset(document):
            raise NativeWeaverProtocolError("native response is missing identity fields")

        strings: dict[str, str] = {}
        for key in required:
            value = document[key]
            if not isinstance(value, str):
                raise NativeWeaverProtocolError(
                    f"native response field {key} must be a string"
                )
            strings[key] = value

        if strings["contract_version"] != CONTRACT_VERSION:
            raise NativeWeaverProtocolError("native response contract version mismatch")
        if not _SHA256_RE.fullmatch(strings["output_sha256"]):
            raise NativeWeaverProtocolError("native response output_sha256 is malformed")

        return BackendActivationResult(
            request_id=strings["request_id"],
            model_id=strings["model_id"],
            backend_id=strings["backend_id"],
            checkpoint_sha256=strings["checkpoint_sha256"],
            output_sha256=strings["output_sha256"],
            primary_metric=_metric(document.get("primary_metric"), "primary_metric"),
            retention_metric=_metric(document.get("retention_metric"), "retention_metric"),
            backend_sha256=library_digest_before,
            contract_version=strings["contract_version"],
        )
