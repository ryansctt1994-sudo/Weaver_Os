from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from weaver_void import (
    ActivationAction,
    ActivationIntent,
    NativeVoidBackend,
    NativeVoidProtocolError,
)

CHECKPOINT = "a" * 64
INPUT = b"bound-native-input"


@pytest.fixture()
def native_library(tmp_path: Path) -> Path:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("C compiler unavailable for native ABI conformance test")
    source = Path(__file__).parent / "fixtures" / "weaver_void_native_fixture.c"
    library = tmp_path / "libweaver_void_fixture.so"
    subprocess.run(
        [compiler, "-shared", "-fPIC", "-O2", str(source), "-o", str(library)],
        check=True,
        capture_output=True,
    )
    return library


def make_intent(library: Path, *, input_sha256: str | None = None) -> ActivationIntent:
    return ActivationIntent(
        request_id="req-native",
        model_id="m1",
        backend_id="void-native-c",
        action=ActivationAction.INFER,
        checkpoint_sha256=CHECKPOINT,
        input_sha256=input_sha256 or hashlib.sha256(INPUT).hexdigest(),
        backend_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
    )


def test_native_abi_executes_with_binary_and_input_binding(native_library: Path) -> None:
    backend = NativeVoidBackend(native_library, INPUT)
    intent = make_intent(native_library)
    result = backend(intent)
    assert result.request_id == intent.request_id
    assert result.checkpoint_sha256 == intent.checkpoint_sha256
    assert result.backend_sha256 == intent.backend_sha256
    assert result.output_sha256 == "c" * 64
    assert result.retention_metric == pytest.approx(0.999)


def test_native_abi_rejects_binary_substitution(native_library: Path) -> None:
    intent = make_intent(native_library)
    intent = ActivationIntent(
        request_id=intent.request_id,
        model_id=intent.model_id,
        backend_id=intent.backend_id,
        action=intent.action,
        checkpoint_sha256=intent.checkpoint_sha256,
        input_sha256=intent.input_sha256,
        backend_sha256="d" * 64,
    )
    with pytest.raises(NativeVoidProtocolError, match="backend digest"):
        NativeVoidBackend(native_library, INPUT)(intent)


def test_native_abi_rejects_input_substitution(native_library: Path) -> None:
    intent = make_intent(native_library, input_sha256="e" * 64)
    with pytest.raises(NativeVoidProtocolError, match="input bytes"):
        NativeVoidBackend(native_library, INPUT)(intent)
