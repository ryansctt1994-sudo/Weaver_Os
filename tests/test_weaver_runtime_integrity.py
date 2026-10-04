from __future__ import annotations

import sys
from pathlib import Path

import pytest

from weaver_activation.runtime_integrity import (
    RuntimeIntegrityError,
    assert_clean_loader_environment,
    assert_linux_library_mapping_integrity,
)


def test_loader_environment_rejects_preload() -> None:
    with pytest.raises(RuntimeIntegrityError, match="LD_PRELOAD"):
        assert_clean_loader_environment({"LD_PRELOAD": "/tmp/interposer.so"})


def test_loader_environment_accepts_empty_values() -> None:
    assert_clean_loader_environment({"LD_PRELOAD": "", "LD_LIBRARY_PATH": ""})


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc mapping check")
def test_mapping_check_rejects_unmapped_regular_file(tmp_path: Path) -> None:
    candidate = tmp_path / "not-loaded.so"
    candidate.write_bytes(b"not an elf")
    with pytest.raises(RuntimeIntegrityError, match="not mapped"):
        assert_linux_library_mapping_integrity(candidate)
