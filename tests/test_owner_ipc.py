"""WEAVER-V008 first slice: unprivileged checks of the IPC primitives.

These run as any user, on every CI Python version. The cross-uid acceptance tests that need
root live in tests/isolation/. Nothing here claims OS-level confinement.
"""
from __future__ import annotations

import os
import socket
import struct
import sys

import pytest
from weaver_runtime.owner_ipc import (
    MAX_FRAME_BYTES,
    FrameError,
    UntrustedPathError,
    assert_trusted_path,
    encode_frame,
    load_strict_json,
    peer_credentials,
    recv_frame,
)

linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SO_PEERCRED")


def _pair():
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    a.settimeout(2)
    b.settimeout(2)
    return a, b


def test_frame_round_trip():
    a, b = _pair()
    with a, b:
        a.sendall(encode_frame({"op": "rows", "n": [1, 2, 3]}))
        assert recv_frame(b) == {"op": "rows", "n": [1, 2, 3]}


@pytest.mark.parametrize(
    "text",
    ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', "not json", '{"a":', "﻿{}"],
)
def test_strict_json_refuses_ambiguous_or_invalid_text(text):
    with pytest.raises(FrameError):
        load_strict_json(text)


def test_oversized_zero_and_truncated_frames_are_refused():
    a, b = _pair()
    with a, b:
        a.sendall(struct.pack(">I", MAX_FRAME_BYTES + 1))
        with pytest.raises(FrameError):
            recv_frame(b)
    a, b = _pair()
    with a, b:
        a.sendall(struct.pack(">I", 0))
        with pytest.raises(FrameError):
            recv_frame(b)
    a, b = _pair()
    with a, b:
        a.sendall(struct.pack(">I", 50) + b"{}")
        a.close()
        with pytest.raises(FrameError):
            recv_frame(b)
    with pytest.raises(FrameError):
        encode_frame({"x": "y" * MAX_FRAME_BYTES})
    with pytest.raises(FrameError):
        encode_frame({"x": float("nan")})


def test_non_utf8_frame_is_refused():
    a, b = _pair()
    with a, b:
        a.sendall(struct.pack(">I", 2) + b"\xff\xfe")
        with pytest.raises(FrameError):
            recv_frame(b)


@linux_only
def test_peer_credentials_report_this_process():
    a, b = _pair()
    with a, b:
        creds = peer_credentials(a)
    assert (creds.pid, creds.uid, creds.gid) == (os.getpid(), os.getuid(), os.getgid())


def _tmp_chain(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    base.chmod(0o755)
    return base


@linux_only
def test_trusted_path_accepts_a_private_chain_owned_by_the_caller(tmp_path):
    base = _tmp_chain(tmp_path)
    private = base / "private"
    private.mkdir(mode=0o700)
    secret = private / "owner.json"
    secret.write_text("{}")
    secret.chmod(0o600)
    uid = os.geteuid()
    assert_trusted_path(private, uid, leaf="private_dir")
    assert_trusted_path(secret, uid, leaf="private_file")
    assert_trusted_path(base, uid, leaf="public_dir")


@linux_only
def test_trusted_path_refuses_symlinked_leaf_and_symlinked_ancestor(tmp_path):
    base = _tmp_chain(tmp_path)
    real = base / "real"
    real.mkdir(mode=0o700)
    (base / "link").symlink_to(real)
    uid = os.geteuid()
    with pytest.raises(UntrustedPathError, match="symlink"):
        assert_trusted_path(base / "link", uid, leaf="private_dir")
    with pytest.raises(UntrustedPathError, match="symlink"):
        assert_trusted_path(base / "link" / "x", uid, leaf="private_file")


@linux_only
def test_trusted_path_refuses_a_group_or_other_writable_ancestor(tmp_path):
    base = _tmp_chain(tmp_path)
    shared = base / "shared"
    shared.mkdir()
    shared.chmod(0o777)  # writable by anyone and NOT sticky: entries can be swapped
    inner = shared / "inner"
    inner.mkdir(mode=0o700)
    with pytest.raises(UntrustedPathError, match="writable"):
        assert_trusted_path(inner, os.geteuid(), leaf="private_dir")


@linux_only
def test_trusted_path_refuses_wrong_kind_wrong_owner_and_loose_modes(tmp_path):
    base = _tmp_chain(tmp_path)
    uid = os.geteuid()
    loose = base / "loose"
    loose.mkdir(mode=0o755)
    loose.chmod(0o755)  # mkdir's requested mode is filtered by the process umask.
    with pytest.raises(UntrustedPathError, match="mode"):
        assert_trusted_path(loose, uid, leaf="private_dir")
    plain = base / "plain"
    plain.write_text("x")
    plain.chmod(0o600)
    with pytest.raises(UntrustedPathError, match="expected kind"):
        assert_trusted_path(plain, uid, leaf="private_dir")
    with pytest.raises(UntrustedPathError, match="owned by uid"):
        assert_trusted_path(plain, uid + 1, leaf="private_file")
    with pytest.raises(UntrustedPathError, match="cannot stat"):
        assert_trusted_path(base / "missing", uid, leaf="private_file")
    with pytest.raises(ValueError):
        assert_trusted_path(base, uid, leaf="whatever")
