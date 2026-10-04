"""Runtime-integrity tripwires for the native activation seam.

These checks narrow the in-process threat surface. They do not prove arbitrary
process-memory integrity and cannot remove an interposer that was loaded before
the current process started.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_DANGEROUS_LOADER_ENV = (
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "LD_DEBUG",
    "LD_PROFILE",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
)


class RuntimeIntegrityError(RuntimeError):
    """Raised when a native runtime-integrity tripwire fails."""


def assert_clean_loader_environment(
    environment: Mapping[str, str] | None = None,
) -> None:
    env = os.environ if environment is None else environment
    present = sorted(name for name in _DANGEROUS_LOADER_ENV if env.get(name))
    if present:
        raise RuntimeIntegrityError(
            "unsafe dynamic-loader environment: " + ", ".join(present)
        )


@dataclass(frozen=True)
class LinuxMapEntry:
    permissions: str
    device_major: int
    device_minor: int
    inode: int
    path: str


def _parse_linux_maps(text: str) -> list[LinuxMapEntry]:
    entries: list[LinuxMapEntry] = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5:
            continue
        _address, permissions, _offset, device, inode_text = fields[:5]
        path = fields[5] if len(fields) == 6 else ""
        if ":" not in device:
            continue
        major_text, minor_text = device.split(":", 1)
        try:
            entries.append(
                LinuxMapEntry(
                    permissions=permissions,
                    device_major=int(major_text, 16),
                    device_minor=int(minor_text, 16),
                    inode=int(inode_text),
                    path=path,
                )
            )
        except ValueError:
            continue
    return entries


def assert_linux_library_mapping_integrity(library_path: Path) -> None:
    """Check that Linux mapped the expected inode and did not grant W+X.

    This validates mapping identity/permissions for the target shared library.
    It does not hash relocated executable pages and is not a general proof that
    every mapped dependency or preloaded object is trustworthy.
    """

    if not sys.platform.startswith("linux"):
        return

    maps_path = Path("/proc/self/maps")
    try:
        maps_text = maps_path.read_text()
        target = library_path.resolve(strict=True)
        stat = target.stat()
    except OSError as exc:
        raise RuntimeIntegrityError("unable to inspect Linux process mappings") from exc

    expected_major = os.major(stat.st_dev)
    expected_minor = os.minor(stat.st_dev)
    matches: list[LinuxMapEntry] = []

    for entry in _parse_linux_maps(maps_text):
        if not entry.path:
            continue
        raw_path = entry.path
        if raw_path.endswith(" (deleted)"):
            candidate_text = raw_path[: -len(" (deleted)")]
            deleted = True
        else:
            candidate_text = raw_path
            deleted = False
        try:
            candidate = Path(candidate_text).resolve()
        except OSError:
            continue
        if candidate != target:
            continue
        if deleted:
            raise RuntimeIntegrityError("native library mapping was deleted after load")
        if (
            entry.inode != stat.st_ino
            or entry.device_major != expected_major
            or entry.device_minor != expected_minor
        ):
            raise RuntimeIntegrityError("native library mapping identity mismatch")
        if "w" in entry.permissions and "x" in entry.permissions:
            raise RuntimeIntegrityError("native library has writable+executable mapping")
        matches.append(entry)

    if not matches:
        raise RuntimeIntegrityError("native library is not mapped from the pinned path")
    if not any("x" in entry.permissions for entry in matches):
        raise RuntimeIntegrityError("native library has no executable mapping")
