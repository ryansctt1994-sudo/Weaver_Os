"""WEAVER-V008 first slice: unprivileged checks of the IPC primitives.

These run as any user, on every CI Python version. The cross-uid acceptance tests that need
root live in tests/isolation/. Nothing here claims OS-level confinement.
"""
from __future__ import annotations

import json
import os
import socket
import struct
import sys

import pytest
from weaver_runtime import owner_ipc
from weaver_runtime.owner_ipc import (
    MAX_FRAME_BYTES,
    MAX_JSON_DEPTH,
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


def _nested_arrays(n):
    return "[" * n + "]" * n


def _nested_objects(n, leaf='"x[{]}\\"y"'):
    # n nested objects around a leaf string that is itself full of structural characters.
    return '{"k":' * n + leaf + "}" * n


def test_json_nesting_depth_32_is_accepted_and_33_is_refused():
    # The boundary is exact. Depth 32 is the deepest accepted; the 33rd open container is
    # refused the moment it opens. Strings carrying brackets and an escaped quote sit inside
    # the nesting to prove they do not shift where the boundary falls.
    assert MAX_JSON_DEPTH == 32
    assert load_strict_json(_nested_arrays(32)) == json.loads(_nested_arrays(32))
    assert load_strict_json(_nested_objects(32))  # 32 objects around a bracket-laden string
    with pytest.raises(FrameError, match="deeper than 32"):
        load_strict_json(_nested_arrays(33))
    with pytest.raises(FrameError, match="deeper than 32"):
        load_strict_json(_nested_objects(33))


def test_structural_characters_inside_strings_do_not_count_toward_depth():
    # One object, whose string value holds an escaped quote followed by 40 [{ pairs. Correct
    # escape handling keeps the whole thing at depth 1; handling that mistook \" for the end
    # of the string would read 80 open containers and refuse a valid, shallow request.
    payload = '{"s": "x\\"' + "[{" * 40 + '"}'
    assert json.loads(payload) == {"s": 'x"' + "[{" * 40}  # it really is valid, shallow JSON
    assert load_strict_json(payload) == {"s": 'x"' + "[{" * 40}
    # A giant run of structural characters, all inside one string, is still depth 1.
    big = '{"s": "' + "[{" * 2000 + '\\"' + "]}" * 2000 + '"}'
    assert load_strict_json(big)["s"].startswith("[{")


def test_a_parser_recursion_error_is_converted_to_a_frame_error(monkeypatch):
    # Defence in depth: if any payload reached the parser and recursed, the RecursionError
    # must come back as the same malformed-input error, never escape. The probe is shallow,
    # so it clears the depth scan and the conversion is what is under test, not the scan.
    real_loads = json.loads
    probe = '{"x": 1}'

    def fake_loads(text, *args, **kwargs):
        if text == probe:
            raise RecursionError("maximum recursion depth exceeded")
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr(owner_ipc.json, "loads", fake_loads)
    with pytest.raises(FrameError, match="too deep for the parser"):
        load_strict_json(probe)


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
