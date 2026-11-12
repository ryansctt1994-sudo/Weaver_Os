"""V008 service-edge security telemetry: unprivileged checks of the recorder's contract.

Telemetry is private, bounded, best-effort operational evidence. It is not a receipt and
never part of an authorization decision. These tests run as any user, on every CI Python
version; the cross-uid tests with real peer processes are in
tests/isolation/test_v008_edge_telemetry.py.
"""
from __future__ import annotations

import json
import os
import socket
import stat
import sys
import time

import pytest
from weaver_runtime.owner_ipc import PeerCredentials, encode_frame, recv_frame
from weaver_runtime.owner_service import OwnerService
from weaver_runtime.owner_telemetry import (
    ACTOR_DENIED,
    DEADLINE_EXCEEDED,
    EVENT_CLASSES,
    FRAME_REJECTED,
    MAX_FILE_BYTES,
    OTHER,
    PEER_DENIED,
    REQUEST_REJECTED,
    EdgeTelemetry,
    TelemetryUnsafe,
)

linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SO_PEERCRED")


@pytest.fixture
def path(tmp_path):
    return tmp_path / "edge-telemetry.json"


def make(path, **kwargs):
    kwargs.setdefault("flush_interval", 0.05)
    return EdgeTelemetry(path, **kwargs)


def test_the_five_event_classes_are_a_separate_namespace():
    assert EVENT_CLASSES == (
        PEER_DENIED, FRAME_REJECTED, REQUEST_REJECTED, ACTOR_DENIED, DEADLINE_EXCEEDED
    )
    assert "REFUSED" not in EVENT_CLASSES and "COMMITTED" not in EVENT_CLASSES


def test_unknown_event_classes_are_refused(path):
    t = make(path)
    try:
        with pytest.raises(ValueError):
            t.record("REFUSED", 1000, 1)
    finally:
        t.close()


def test_counts_are_exact_for_processed_events(path):
    t = make(path)
    for _ in range(7):
        t.record(PEER_DENIED, 61003, 11)
    for _ in range(3):
        t.record(ACTOR_DENIED, 61002, 12)
    snap = t.snapshot()
    t.close()
    assert snap["counters"]["61003"] == {PEER_DENIED: 7}
    assert snap["counters"]["61002"] == {ACTOR_DENIED: 3}
    assert snap["events_observed"] == 10


def test_uid_cardinality_cap_is_deterministic_and_never_moves_counts(path):
    t = make(path, max_uids=2)
    for uid in (10, 11, 12, 13, 10):
        t.record(FRAME_REJECTED, uid, 1)
    snap = t.snapshot()
    t.close()
    # The first two distinct uids are retained; later ones go to "other", and stay there.
    assert snap["retained_uids"] == [10, 11]
    assert snap["counters"]["10"] == {FRAME_REJECTED: 2}
    assert snap["counters"]["11"] == {FRAME_REJECTED: 1}
    assert snap["counters"][OTHER] == {FRAME_REJECTED: 2}
    assert snap["events_observed"] == 5


def test_counters_saturate_deterministically_and_say_so(path):
    t = make(path, max_count=5)
    for _ in range(9):
        t.record(REQUEST_REJECTED, 61002, 1)
    snap = t.snapshot()
    t.close()
    assert snap["counters"]["61002"] == {REQUEST_REJECTED: 5}
    assert snap["saturated"] == ["61002|REQUEST_REJECTED", "events_observed"]
    assert snap["events_observed"] == 5


def test_structures_stay_bounded_under_many_uids_and_events(path):
    t = make(path, max_uids=8, max_recent=16)
    for uid in range(1000):
        for _ in range(10):
            t.record(PEER_DENIED, uid, uid)
    snap = t.snapshot()
    t.close()
    assert len(snap["counters"]) == 9  # 8 retained + other
    assert len(snap["recent"]) == 16
    assert snap["events_observed"] == 10_000
    assert sum(row[PEER_DENIED] for row in snap["counters"].values()) == 10_000


def test_records_carry_only_kernel_identity_and_fixed_words(path):
    t = make(path)
    t.record(ACTOR_DENIED, 61002, 4242)
    snap = t.snapshot()
    t.close()
    (entry,) = snap["recent"]
    assert set(entry) == {"seq", "class", "uid", "pid", "at"}
    assert (entry["class"], entry["uid"], entry["pid"]) == (ACTOR_DENIED, 61002, 4242)


@pytest.mark.parametrize("bad", [-1, True, "61002", 1.5, 2**32])
def test_identity_must_be_a_kernel_style_integer(path, bad):
    t = make(path)
    try:
        with pytest.raises(ValueError):
            t.record(PEER_DENIED, bad, 1)
    finally:
        t.close()


def test_persisted_file_is_private_bounded_valid_json(path):
    t = make(path)
    for uid in range(100):
        t.record(FRAME_REJECTED, uid, uid)
    summary = t.close()
    assert summary["last_persist"] == "ok" and summary["shutdown_flush"] == "ok"
    st = os.lstat(path)
    assert stat.S_ISREG(st.st_mode) and st.st_mode & 0o077 == 0
    assert st.st_size <= MAX_FILE_BYTES
    data = json.loads(path.read_text())
    assert data["schema"] == "weaver-edge-telemetry-1"
    assert data["events_observed"] == 100


def test_a_planted_symlink_at_the_temp_path_is_never_followed(path, tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched")
    t = make(path)
    os.symlink(victim, f"{path}.tmp")
    t.record(PEER_DENIED, 1, 1)
    summary = t.close()
    assert victim.read_text() == "untouched"
    assert summary["persist_failures"] >= 1 and summary["last_persist"] == "failed"


def test_a_valid_file_is_carried_over(path):
    t = make(path)
    for _ in range(4):
        t.record(PEER_DENIED, 61003, 1)
    t.close()
    again = make(path)
    again.record(PEER_DENIED, 61003, 1)
    snap = again.snapshot()
    again.close()
    assert snap["carried_over"] is True
    assert snap["counters"]["61003"] == {PEER_DENIED: 5}
    assert snap["events_observed"] == 5


@pytest.mark.parametrize("counters", [[], None, "invalid", True, 1.5])
def test_invalid_counter_container_is_recovered_and_new_events_persist(path, counters):
    original = make(path)
    original.record(PEER_DENIED, 61003, 11)
    original.close()
    data = json.loads(path.read_text())
    data["counters"] = counters
    corrupted = json.dumps(data)
    path.write_text(corrupted)

    restored = make(path)
    try:
        snap = restored.snapshot()
        assert snap["corrupt_recovered"] is True
        assert snap["events_observed"] == 0
        assert snap["counters"] == {}
        assert path.with_name(path.name + ".corrupt").read_text() == corrupted
        restored.record(FRAME_REJECTED, 61002, 12)
    finally:
        summary = restored.close()
    assert summary["last_persist"] == "ok"
    assert json.loads(path.read_text())["counters"] == {"61002": {FRAME_REJECTED: 1}}


def test_a_corrupt_file_is_set_aside_and_counting_restarts(path):
    path.write_text("{not json")
    os.chmod(path, 0o600)
    t = make(path)
    snap = t.snapshot()
    t.close()
    assert snap["corrupt_recovered"] is True and snap["events_observed"] == 0
    assert os.path.exists(f"{path}.corrupt")


def test_a_planted_fifo_is_refused_without_blocking(path):
    import threading

    os.mkfifo(path, 0o600)  # a blocking open for read would hang the owner at start-up
    outcome: list[BaseException | None] = []

    def attempt():
        try:
            make(path)
            outcome.append(None)
        except BaseException as exc:
            outcome.append(exc)

    worker = threading.Thread(target=attempt, daemon=True)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive(), "the recorder blocked opening a FIFO"
    assert len(outcome) == 1 and isinstance(outcome[0], TelemetryUnsafe), outcome


@pytest.mark.parametrize("problem", ["symlink", "loose-mode", "hard-link"])
def test_an_unsafe_existing_file_refuses_to_load(path, tmp_path, problem):
    if problem == "symlink":
        target = tmp_path / "elsewhere.json"
        target.write_text("{}")
        os.symlink(target, path)
    else:
        path.write_text("{}")
        os.chmod(path, 0o644 if problem == "loose-mode" else 0o600)
        if problem == "hard-link":
            os.link(path, tmp_path / "second-name.json")
    with pytest.raises(TelemetryUnsafe):
        make(path)


def test_a_stale_temp_file_is_removed_but_a_temp_symlink_refuses(path, tmp_path):
    stale = f"{path}.tmp"
    with open(stale, "w") as handle:
        handle.write("half a snapshot")
    os.chmod(stale, 0o600)
    t = make(path)
    t.close()
    assert not os.path.lexists(stale)
    os.symlink(tmp_path / "x", stale)
    with pytest.raises(TelemetryUnsafe):
        make(path)


def test_a_hung_write_cannot_hold_shutdown_past_its_timeout(path):
    t = make(path, fault="persist-hangs")
    t.record(PEER_DENIED, 1, 1)
    time.sleep(0.2)  # the writer is now stuck in its write
    started = time.monotonic()
    summary = t.close(timeout=0.5)
    assert time.monotonic() - started < 2.0
    assert summary["shutdown_flush"] == "timed-out"
    assert "shutdown-flush-timed-out" in summary["degraded"]


def test_a_failing_write_is_counted_and_reported(path):
    t = make(path, fault="persist-fails")
    t.record(PEER_DENIED, 1, 1)
    summary = t.close()
    assert summary["persist_failures"] >= 1 and summary["last_persist"] == "failed"
    assert not os.path.lexists(path)


def test_record_fault_raises(path):
    t = make(path, fault="record-fails")
    try:
        with pytest.raises(OSError):
            t.record(PEER_DENIED, 1, 1)
    finally:
        t.close()


def test_reserved_uids_keep_dedicated_counters_when_the_cap_is_exhausted(path):
    t = make(path, max_uids=2, reserved_uids=frozenset({61002}))
    for uid in (10, 11, 12, 13):  # unlisted: two retained, two counted in "other"
        t.record(PEER_DENIED, uid, 1)
    for _ in range(3):  # the listed principal arrives AFTER the cap is full
        t.record(ACTOR_DENIED, 61002, 1)
    snap = t.snapshot()
    t.close()
    assert snap["counters"]["61002"] == {ACTOR_DENIED: 3}
    assert snap["counters"][OTHER] == {PEER_DENIED: 2}
    assert snap["retained_uids"] == [10, 11] and snap["reserved_uids"] == [61002]


def test_load_folds_dropped_uids_into_other_exactly_once_and_keeps_totals(path):
    t = make(path, max_uids=8)
    for uid, n in ((1, 3), (2, 4), (3, 5)):
        for _ in range(n):
            t.record(FRAME_REJECTED, uid, 1)
    t.record(PEER_DENIED, 1, 1)
    t.close()
    again = make(path, max_uids=1, reserved_uids=frozenset({3}))  # 1 retained, 3 reserved
    snap = again.snapshot()
    again.close()  # persists the folded state
    assert snap["counters"] == {
        "1": {FRAME_REJECTED: 3, PEER_DENIED: 1},
        "3": {FRAME_REJECTED: 5},
        OTHER: {FRAME_REJECTED: 4},
    }
    assert snap["retained_uids"] == [1] and snap["folded_uids"] == 1
    assert snap["events_observed"] == 13  # the aggregate never moves
    third = make(path, max_uids=1, reserved_uids=frozenset({3}))
    s3 = third.snapshot()
    third.close()
    assert s3["counters"] == snap["counters"] and s3["folded_uids"] == 0  # no double fold


def test_a_retained_uid_that_becomes_reserved_keeps_its_counters(path):
    t = make(path, max_uids=2)
    t.record(PEER_DENIED, 5, 1)
    t.record(PEER_DENIED, 6, 1)
    t.close()
    again = make(path, max_uids=2, reserved_uids=frozenset({5}))
    snap = again.snapshot()
    again.close()
    assert snap["retained_uids"] == [6] and snap["reserved_uids"] == [5]
    assert snap["counters"]["5"] == {PEER_DENIED: 1} and snap["folded_uids"] == 0


def test_a_fold_that_would_overflow_saturates_and_says_so(path):
    t = make(path, max_uids=8, max_count=10)
    for uid in (1, 2, 3):
        for _ in range(7):
            t.record(FRAME_REJECTED, uid, 1)
    t.close()
    again = make(path, max_uids=1, max_count=10)  # uids 2 and 3 fold: 14 > 10
    snap = again.snapshot()
    again.close()
    assert snap["counters"][OTHER] == {FRAME_REJECTED: 10}
    assert f"{OTHER}|{FRAME_REJECTED}" in snap["saturated"]


def test_a_failed_snapshot_is_not_evidence_and_degradation_rides_the_next_success(path):
    t = make(path, fault="persist-fails-once")
    t.record(PEER_DENIED, 1, 1)
    time.sleep(0.4)
    assert not os.path.lexists(path)  # nothing durable says a failure ever occurred
    assert t.snapshot()["degraded"] == ["persist-failed"]  # but it is visible in memory
    t.record(PEER_DENIED, 1, 1)
    time.sleep(0.4)
    on_disk = json.loads(path.read_text())
    t.close()
    assert on_disk["degraded"] == ["persist-failed"] and on_disk["persist_failures"] == 1
    assert on_disk["events_observed"] == 2


def test_a_failed_directory_sync_is_degraded_never_durable_success(path):
    t = make(path, fault="dir-fsync-fails")
    t.record(PEER_DENIED, 1, 1)
    summary = t.close()
    assert os.path.lexists(path)  # the replacement happened, so the contents are present...
    assert json.loads(path.read_text())["events_observed"] == 1
    assert summary["last_persist"] == "unsynced"  # ...but durability is not claimed
    assert summary["degraded"] == ["dir-fsync-failed"] and summary["persist_failures"] >= 1


def test_the_recorder_refuses_a_parent_directory_that_is_not_private(tmp_path):
    loose = tmp_path / "loose"
    loose.mkdir()
    os.chmod(loose, 0o755)
    with pytest.raises(TelemetryUnsafe):
        make(loose / "edge.json")


def test_the_recorder_refuses_a_symlinked_parent(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "link"
    os.symlink(real, link)
    with pytest.raises(TelemetryUnsafe):
        make(link / "edge.json")


def test_a_swapped_parent_path_cannot_redirect_later_writes(tmp_path):
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    t = make(data / "edge.json")
    moved = tmp_path / "data.moved"
    os.rename(data, moved)  # the path now names a different directory...
    decoy = tmp_path / "data"
    decoy.mkdir(mode=0o700)
    t.record(PEER_DENIED, 1, 1)
    summary = t.close()
    assert summary["last_persist"] == "ok"
    assert (moved / "edge.json").exists()  # ...but writes stayed in the directory it opened
    assert os.listdir(decoy) == []


class _NoOwner:
    def rows(self):
        return {}


class _BrokenTelemetry:
    def __init__(self):
        self.calls = 0

    def record(self, event_class, uid, pid):
        self.calls += 1
        raise OSError("recorder broken")


@linux_only
def test_a_broken_recorder_never_changes_the_decision_or_stops_the_owner(tmp_path):
    broken = _BrokenTelemetry()
    service = OwnerService(
        tmp_path / "unused.sock", _NoOwner(),  # type: ignore[arg-type]
        peers={os.geteuid(): frozenset({"agent-a"})},
        request_deadline=0.5, reply_deadline=0.5,
        telemetry=broken,  # type: ignore[arg-type]
    )
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with server, client:
        client.sendall(encode_frame({"op": "telemetry"}))
        service.handle(server)  # must not raise
        client.settimeout(2)
        assert recv_frame(client) == {"ok": False, "error": "bad-request"}
    assert broken.calls == 1 and service.telemetry_errors == 1


class _SlowTelemetry:
    """A recorder that takes a second: the peer must not have to wait for it."""

    def __init__(self):
        self.recorded: list[str] = []

    def record(self, event_class, uid, pid):
        time.sleep(1.0)
        self.recorded.append(event_class)


def _serve_in_thread(service, server):
    import threading

    worker = threading.Thread(target=service.handle, args=(server,), daemon=True)
    worker.start()
    return worker


@linux_only
def test_a_slow_recorder_never_delays_the_reply(tmp_path):
    slow = _SlowTelemetry()
    service = OwnerService(
        tmp_path / "unused.sock", _NoOwner(),  # type: ignore[arg-type]
        peers={os.geteuid(): frozenset({"agent-a"})},
        request_deadline=2.0, reply_deadline=2.0, telemetry=slow,  # type: ignore[arg-type]
    )
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with server, client:
        client.sendall(encode_frame({"op": "telemetry"}))
        worker = _serve_in_thread(service, server)
        client.settimeout(0.5)  # the reply comes first; recording comes after it
        assert recv_frame(client) == {"ok": False, "error": "bad-request"}
        worker.join(timeout=5)
    assert slow.recorded == [REQUEST_REJECTED]


@linux_only
def test_a_slow_recorder_never_delays_closing_on_an_unlisted_peer(tmp_path):
    slow = _SlowTelemetry()
    service = OwnerService(
        tmp_path / "unused.sock", _NoOwner(),  # type: ignore[arg-type]
        peers={os.geteuid() + 1: frozenset({"agent-a"})},  # this process is not listed
        telemetry=slow,  # type: ignore[arg-type]
    )
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with client:
        worker = _serve_in_thread(service, server)
        client.settimeout(0.5)  # the close comes first; recording comes after it
        assert client.recv(1) == b""
        worker.join(timeout=5)
    assert slow.recorded == [PEER_DENIED]


@linux_only
def test_the_service_records_after_replying_with_kernel_identity(tmp_path):
    t = make(tmp_path / "edge.json")
    service = OwnerService(
        tmp_path / "unused.sock", _NoOwner(),  # type: ignore[arg-type]
        peers={os.geteuid(): frozenset({"agent-a"})},
        request_deadline=0.5, reply_deadline=0.5, telemetry=t,
    )
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with server, client:
        client.sendall(encode_frame({"op": "telemetry", "x": "../../etc\nINJECT"}))
        service.handle(server)
        client.settimeout(2)
        assert recv_frame(client) == {"ok": False, "error": "bad-request"}
    snap = t.snapshot()
    t.close()
    (entry,) = snap["recent"]
    me = PeerCredentials(os.getpid(), os.geteuid(), os.getegid())
    assert (entry["class"], entry["uid"], entry["pid"]) == (REQUEST_REJECTED, me.uid, me.pid)
    assert "INJECT" not in json.dumps(snap)
