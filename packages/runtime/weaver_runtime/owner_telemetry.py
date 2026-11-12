"""WEAVER-V008: service-edge security telemetry for the resource owner.

Research-only. Private, bounded, best-effort operational evidence about requests the owner
turns away at its edge, before they reach the gate. It is NOT a receipt: it is not part of
the hash-chained ledger, it is never read on the way to a decision, and no requester can
read it (no socket operation exposes it). The gate's own refusal receipts and the outcome
protocol are unchanged.

Event classes (a namespace of its own, separate from the gate's REFUSED outcome):

  PEER_DENIED        the kernel-reported peer uid has no service permission
  FRAME_REJECTED     transport or framing violation (oversized, malformed, cut short)
  REQUEST_REJECTED   a parsed request that breaks the service contract
  ACTOR_DENIED       the claimed actor is not one the authenticated peer may speak for
  DEADLINE_EXCEEDED  the request did not arrive before the request deadline

What is recorded: the event class and the kernel-reported uid and pid (SO_PEERCRED), plus
the owner's own sequence number and wall-clock second. Nothing the client sent is
recorded: no claimed proposal ids, actor ids or field values.

Counter contract:
  * In normal operation, counts are exact for every event recorded, up to ``max_count``.
    A counter that reaches ``max_count`` stays there and is listed in ``saturated``.
  * ``reserved_uids`` (the owner's configured service principals) always have dedicated
    counters and never compete for a slot. The first ``max_uids`` distinct OTHER uids get
    their own counters; every later uid counts in the ``other`` bucket, permanently.
    Nothing is evicted while running, so no count moves.
  * On restart, counters carry over only from the last completed write. A uid that is no
    longer reserved and no longer within the retained slots is folded into ``other``
    exactly once: the sums per event class and ``events_observed`` are unchanged (a sum
    above ``max_count`` saturates and says so). The folded state is what the next write
    persists, so a second restart has nothing left to fold. ``folded_uids`` reports it.
  * Recording is in memory. A background writer persists a snapshot (coalesced, at most
    one write per ``flush_interval``) and once more on close. A crash loses whatever was
    recorded after the last completed write.
  * Storage and memory are fixed by the caps, so a snapshot never exceeds
    ``MAX_FILE_BYTES``.

Degradation is visible, and never claimed as durable evidence. ``degraded`` lists, in
memory, every kind of persistence failure this process has seen:
  persist-failed          a snapshot could not be written
  dir-fsync-failed        a snapshot was renamed into place but the directory could not be
                          synced, so it may not survive a crash (written, durability unknown)
  shutdown-flush-timed-out  the final write did not finish in time
A failed write leaves nothing on disk, so it cannot record that it failed: the flag rides
in the NEXT successful snapshot, and in the operator's shutdown line.

Filesystem safety. The recorder acquires its directory ONCE, through a trusted-path walk
(no symlink and no attacker-writable ancestor) followed by an ``O_DIRECTORY | O_NOFOLLOW``
open whose descriptor it checks with ``fstat`` (owner-owned, mode 0700, same device and
inode as the walk saw). Every later operation is relative to that descriptor, so replacing
the path afterwards cannot redirect a write. The file must be a private regular file with
one link, checked on the opened descriptor; a symlink, FIFO or foreign file makes the owner
refuse to start. A safe but unreadable or malformed file is moved to ``<name>.corrupt`` and
counting restarts (``corrupt_recovered``). Writes go to ``<name>.tmp`` created
``O_CREAT | O_EXCL | O_NOFOLLOW``, are fsynced, atomically renamed, and then the directory
is fsynced.
"""
from __future__ import annotations

import collections
import contextlib
import errno
import os
import stat
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from weaver_contracts.canonical import canonicalize

from .owner_ipc import FrameError, UntrustedPathError, assert_trusted_path, load_strict_json

PEER_DENIED = "PEER_DENIED"
FRAME_REJECTED = "FRAME_REJECTED"
REQUEST_REJECTED = "REQUEST_REJECTED"
ACTOR_DENIED = "ACTOR_DENIED"
DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
EVENT_CLASSES = (PEER_DENIED, FRAME_REJECTED, REQUEST_REJECTED, ACTOR_DENIED, DEADLINE_EXCEEDED)

PERSIST_FAILED = "persist-failed"
DIR_FSYNC_FAILED = "dir-fsync-failed"
SHUTDOWN_FLUSH_TIMED_OUT = "shutdown-flush-timed-out"

OTHER = "other"
SCHEMA = "weaver-edge-telemetry-1"
MAX_COUNT = 2**53 - 1  # the largest integer every JSON reader keeps exactly
MAX_FILE_BYTES = 1024 * 1024
_ID_LIMIT = 2**32  # uids and pids are 32-bit
_FAULTS = frozenset(
    {"persist-fails", "persist-fails-once", "persist-hangs", "dir-fsync-fails", "record-fails"}
)


class TelemetryUnsafe(Exception):
    """The telemetry directory, file or temp file is not one the owner can trust."""


def _kernel_id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < _ID_LIMIT:
        raise ValueError("uid and pid must be kernel-style integers")
    return value


class EdgeTelemetry:
    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        reserved_uids: frozenset[int] = frozenset(),
        max_uids: int = 64,
        max_recent: int = 256,
        max_count: int = MAX_COUNT,
        flush_interval: float = 0.5,
        clock: Callable[[], float] = time.time,
        fault: str | None = None,
    ) -> None:
        for name, value, high in (("max_uids", max_uids, 1024),
                                  ("max_recent", max_recent, 1024),
                                  ("max_count", max_count, MAX_COUNT)):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
                raise ValueError(f"{name} must be an integer in [1, {high}]")
        if fault is not None and fault not in _FAULTS:
            raise ValueError(f"unknown telemetry fault {fault!r}")
        if len(reserved_uids) > 1024:
            raise ValueError("at most 1024 reserved uids")
        self._reserved = frozenset(_kernel_id(uid) for uid in reserved_uids)
        full = Path(path)
        if not full.name or full.name in (".", ".."):
            raise ValueError("telemetry path must name a file")
        self._name = full.name
        self._tmp_name = f"{full.name}.tmp"
        self._corrupt_name = f"{full.name}.corrupt"
        self._max_uids = max_uids
        self._max_count = max_count
        self._flush_interval = flush_interval
        self._clock = clock
        self._fault = fault
        self._fault_spent = False
        self._lock = threading.Lock()
        self._counters: dict[str, dict[str, int]] = {}
        self._retained: list[int] = []
        self._saturated: set[str] = set()
        self._recent: collections.deque[dict[str, Any]] = collections.deque(maxlen=max_recent)
        self._observed = 0
        self._seq = 0
        self._folded = 0
        self._carried_over = False
        self._corrupt_recovered = False
        self._persist_failures = 0
        self._last_persist = "none"
        self._degraded: set[str] = set()
        self._started_at = int(clock())
        self._dirfd = self._open_private_dir(full.parent)
        try:
            self._load()
        except BaseException:
            os.close(self._dirfd)
            raise
        self._dirty = threading.Event()
        self._stop = threading.Event()
        self._writer = threading.Thread(target=self._run, name="edge-telemetry", daemon=True)
        self._writer.start()

    # ------------------------------------------------------------------ recording

    def record(self, event_class: str, uid: int, pid: int) -> None:
        """Count one edge event. In memory only: never touches the disk, never blocks."""
        if self._fault == "record-fails":
            raise OSError(errno.EIO, "injected telemetry record failure")
        if event_class not in EVENT_CLASSES:
            raise ValueError(f"unknown edge event class {event_class!r}")
        uid, pid = _kernel_id(uid), _kernel_id(pid)
        with self._lock:
            key = self._bucket(uid)
            row = self._counters.setdefault(key, {})
            if row.get(event_class, 0) >= self._max_count:
                self._saturated.add(f"{key}|{event_class}")
            else:
                row[event_class] = row.get(event_class, 0) + 1
            if self._observed >= self._max_count:
                self._saturated.add("events_observed")
            else:
                self._observed += 1
            if self._seq >= MAX_COUNT:
                self._saturated.add("seq")
            else:
                self._seq += 1
            self._recent.append(
                {"seq": self._seq, "class": event_class, "uid": uid, "pid": pid,
                 "at": int(self._clock())}
            )
        self._dirty.set()

    def _bucket(self, uid: int) -> str:
        if uid in self._reserved:  # configured principals never compete for a slot
            return str(uid)
        if uid in self._retained:
            return str(uid)
        if len(self._retained) < self._max_uids:  # first come, first retained; no eviction
            self._retained.append(uid)
            return str(uid)
        return OTHER

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": SCHEMA,
                "started_at": self._started_at,
                "written_at": int(self._clock()),
                "limits": {"max_uids": self._max_uids, "max_recent": self._recent.maxlen,
                           "max_count": self._max_count},
                "counters": {key: dict(row) for key, row in self._counters.items()},
                "reserved_uids": sorted(self._reserved),
                "retained_uids": list(self._retained),
                "saturated": sorted(self._saturated),
                "events_observed": self._observed,
                "seq": self._seq,
                "folded_uids": self._folded,
                "persist_failures": self._persist_failures,
                "degraded": sorted(self._degraded),
                "carried_over": self._carried_over,
                "corrupt_recovered": self._corrupt_recovered,
                "recent": [dict(entry) for entry in self._recent],
            }

    # ------------------------------------------------------------------ persistence

    def _run(self) -> None:
        while True:
            self._dirty.wait()
            if not self._stop.is_set():
                self._stop.wait(self._flush_interval)  # coalesce a burst into one write
            self._flush_once()
            if self._stop.is_set():
                return

    def _flush_once(self) -> None:
        self._dirty.clear()
        snap = self.snapshot()
        try:
            if self._fault == "persist-hangs":
                threading.Event().wait()  # a write that never returns
            if self._fault == "persist-fails" or (
                self._fault == "persist-fails-once" and not self._fault_spent
            ):
                self._fault_spent = True
                raise OSError(errno.EIO, "injected telemetry write failure")
            self._write(snap)
        except OSError:
            with self._lock:
                self._persist_failures += 1
                self._last_persist = "failed"
                self._degraded.add(PERSIST_FAILED)
            return  # nothing was replaced, so nothing on disk says this failure happened
        try:
            self._sync_dir()
        except OSError:
            # Renamed into place, so the contents are visible, but whether the rename
            # survives a crash is unknown: degraded, never a durable success.
            with self._lock:
                self._persist_failures += 1
                self._last_persist = "unsynced"
                self._degraded.add(DIR_FSYNC_FAILED)
        else:
            with self._lock:
                self._last_persist = "ok"

    def _write(self, snap: dict[str, Any]) -> None:
        data = canonicalize(snap)  # the repository's canonical form (C-CANON-001)
        if len(data) > MAX_FILE_BYTES:
            raise OSError(errno.EFBIG, "telemetry snapshot exceeds its size ceiling")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(self._tmp_name, flags, 0o600, dir_fd=self._dirfd)
        replaced = False
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(
                self._tmp_name, self._name, src_dir_fd=self._dirfd, dst_dir_fd=self._dirfd
            )
            replaced = True
        finally:
            if fd != -1:
                os.close(fd)
            if not replaced:
                with contextlib.suppress(OSError):
                    os.unlink(self._tmp_name, dir_fd=self._dirfd)

    def _sync_dir(self) -> None:
        if self._fault == "dir-fsync-fails":
            raise OSError(errno.EIO, "injected directory sync failure")
        os.fsync(self._dirfd)

    def close(self, timeout: float = 2.0) -> dict[str, Any]:
        """Final flush, bounded by ``timeout``; returns a summary for the operator."""
        self._stop.set()
        self._dirty.set()
        self._writer.join(timeout)
        hung = self._writer.is_alive()
        with self._lock:
            if hung:
                self._degraded.add(SHUTDOWN_FLUSH_TIMED_OUT)
            summary = {
                "events_observed": self._observed,
                "persist_failures": self._persist_failures,
                "last_persist": self._last_persist,
                "shutdown_flush": "timed-out" if hung else "ok",
                "degraded": sorted(self._degraded),
            }
        if not hung:  # a descriptor a stuck writer might still use is never closed under it
            os.close(self._dirfd)
        return summary

    # ------------------------------------------------------------------ loading

    def _open_private_dir(self, directory: Path) -> int:
        uid = os.geteuid()
        try:
            assert_trusted_path(directory, uid, leaf="private_dir")
            seen = os.lstat(directory)
            fd = os.open(
                directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
        except (UntrustedPathError, OSError) as exc:
            raise TelemetryUnsafe(f"edge telemetry directory is unsafe: {exc}") from exc
        st = os.fstat(fd)  # what the descriptor IS, not what the path said a moment ago
        if (
            not stat.S_ISDIR(st.st_mode)
            or st.st_uid != uid
            or st.st_mode & 0o077
            or (st.st_dev, st.st_ino) != (seen.st_dev, seen.st_ino)
        ):
            os.close(fd)
            raise TelemetryUnsafe("edge telemetry directory changed or is not private")
        return fd

    def _open_checked(self, name: str, *, what: str) -> int | None:
        """Open a private regular file inside the directory, judged on the descriptor."""
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        try:
            fd = os.open(name, flags, dir_fd=self._dirfd)
        except FileNotFoundError:
            return None
        except OSError as exc:  # ELOOP means a symlink; anything else is not ours to read
            raise TelemetryUnsafe(f"{what} cannot be opened safely: {exc.strerror}") from exc
        st = os.fstat(fd)
        if (
            not stat.S_ISREG(st.st_mode)
            or st.st_uid != os.geteuid()
            or st.st_mode & 0o077
            or st.st_nlink != 1
        ):
            os.close(fd)
            raise TelemetryUnsafe(f"{what} is not a private regular file with one link")
        return fd

    def _load(self) -> None:
        stale = self._open_checked(self._tmp_name, what="edge telemetry temp file")
        if stale is not None:  # a write the previous owner never finished
            os.close(stale)
            os.unlink(self._tmp_name, dir_fd=self._dirfd)
        fd = self._open_checked(self._name, what="edge telemetry file")
        if fd is None:
            return
        try:
            with os.fdopen(fd, "rb") as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError("oversized")
            self._restore(load_strict_json(raw.decode("utf-8")))
        except (OSError, ValueError, UnicodeDecodeError, FrameError, KeyError, TypeError):
            os.replace(
                self._name, self._corrupt_name, src_dir_fd=self._dirfd, dst_dir_fd=self._dirfd
            )
            self._counters, self._retained, self._saturated = {}, [], set()
            self._observed = self._seq = self._folded = 0
            self._corrupt_recovered = True

    def _restore(self, data: Any) -> None:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise ValueError("not an edge telemetry file")
        stored: dict[str, dict[str, int]] = {}
        for key, row in data["counters"].items():
            if key != OTHER and (not key.isdecimal() or int(key) >= _ID_LIMIT):
                raise ValueError("bad counter key")
            if not isinstance(row, dict) or not set(row) <= set(EVENT_CLASSES):
                raise ValueError("bad counter row")
            stored[key] = {cls: self._count(n) for cls, n in row.items()}
        retained_in = [_kernel_id(uid) for uid in data["retained_uids"]]
        if len(set(retained_in)) != len(retained_in):
            raise ValueError("bad retained uids")
        saturated = data["saturated"]
        if not isinstance(saturated, list) or not all(isinstance(s, str) for s in saturated):
            raise ValueError("bad saturated list")
        observed = self._count(data["events_observed"])
        seq = self._count(data["seq"], MAX_COUNT)  # a sequence number, not a counter

        # Reserved uids keep dedicated counters; the cap applies to the others only.
        retained = [uid for uid in retained_in if uid not in self._reserved][: self._max_uids]
        keep = {str(uid) for uid in self._reserved} | {str(uid) for uid in retained}
        counters: dict[str, dict[str, int]] = {}
        other: dict[str, int] = {}
        folded = 0
        for key, row in stored.items():
            if key == OTHER or key not in keep:
                folded += key != OTHER
                for cls, n in row.items():
                    other[cls] = other.get(cls, 0) + n
            else:
                counters[key] = row
        marks = set()
        for mark in saturated:
            who, _, cls = mark.partition("|")
            if who in ("events_observed", "seq") or who == OTHER or who in keep:
                marks.add(mark)
            elif cls in EVENT_CLASSES:  # a folded uid's saturation moves with its counts
                marks.add(f"{OTHER}|{cls}")
        for cls, n in list(other.items()):
            if n > self._max_count:
                other[cls] = self._max_count
                marks.add(f"{OTHER}|{cls}")
        if other:
            counters[OTHER] = other
        self._counters, self._retained, self._saturated = counters, retained, marks
        self._observed, self._seq, self._folded = observed, seq, folded
        self._carried_over = True

    def _count(self, value: Any, high: int | None = None) -> int:
        ceiling = self._max_count if high is None else high
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= ceiling:
            raise ValueError("bad count")
        return value
