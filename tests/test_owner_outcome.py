"""V008 crash-recovery slice: unprivileged checks of outcome lookup and client semantics.

These run as any user, on every CI Python version. The tests that kill real owner and
requester processes under distinct uids live in tests/isolation/ and need root.
"""
from __future__ import annotations

import base64
import hashlib
import os
import socket
import sys
import threading

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import Proposal
from weaver_runtime.gate import COMMITTED as ATTEMPT_COMMITTED
from weaver_runtime.owner_ipc import (
    IpcError,
    OutcomeUnknown,
    OwnerClient,
    OwnerUnavailable,
    encode_frame,
    recv_frame,
)
from weaver_runtime.owner_outcome import (
    COMMITTED,
    CONFLICT,
    REFUSED,
    UNKNOWN,
    OutcomeError,
    lookup_outcome,
    proposal_digest,
)
from weaver_runtime.protected_write import GRANT_DOMAIN, ProtectedWriteOwner

linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SO_PEERCRED")


class Clear:
    def vetoed(self) -> bool:
        return False


@pytest.fixture
def owner_and_key(tmp_path):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    owner = ProtectedWriteOwner(
        tmp_path / "owner.db", trusted_public_key=public, issuer_id="issuer-a",
        allowed_keys=frozenset({"alpha"}), veto=Clear(), clock=lambda: 1000,
    )
    yield owner, key
    owner.close()


def proposal(pid="p1", value="one"):
    return Proposal(pid, "agent-a", "WRITE_KEY", "policy-v1", {"key": "alpha", "value": value})


def grant(key, p):
    fields = {
        "issuer_id": "issuer-a",
        "audience": "weaver-vertical-001",
        "grant_id": f"g-{p.proposal_id}",
        "proposal_sha256": hashlib.sha256(canonicalize(p.to_dict())).hexdigest(),
        "valid_from": 900, "valid_until": 1100,
    }
    signature = key.sign(GRANT_DOMAIN + canonicalize(fields))
    return {"grant": fields, "signature": base64.urlsafe_b64encode(signature).decode("ascii")}


def test_unseen_proposal_is_unknown_not_refused(owner_and_key):
    owner, _key = owner_and_key
    found = lookup_outcome(owner.snapshot(), "never-sent")
    assert (found["status"], found["final"], found["receipt"]) == (UNKNOWN, False, None)


def test_commit_is_reported_with_its_own_receipt(owner_and_key):
    owner, key = owner_and_key
    p = proposal()
    attempt = owner.submit(p, grant(key, p))
    assert attempt.status == ATTEMPT_COMMITTED
    found = lookup_outcome(owner.snapshot(), "p1")
    assert found["status"] == COMMITTED and found["final"] is True
    assert found["receipt"]["receipt_digest"] == attempt.receipt.receipt_digest
    assert found["proposal_sha256"] == proposal_digest(p.to_dict())


def test_refusal_is_reported_as_not_final_and_a_later_commit_wins(owner_and_key):
    owner, key = owner_and_key
    p = proposal()
    assert owner.submit(p, None).status != ATTEMPT_COMMITTED
    refused = lookup_outcome(owner.snapshot(), "p1")
    assert (refused["status"], refused["final"], refused["refused_attempts"]) == (REFUSED, False, 1)
    assert owner.submit(p, grant(key, p)).status == ATTEMPT_COMMITTED
    found = lookup_outcome(owner.snapshot(), "p1")
    assert (found["status"], found["refused_attempts"]) == (COMMITTED, 1)


def test_duplicate_after_commit_keeps_the_original_receipt(owner_and_key):
    owner, key = owner_and_key
    p = proposal()
    signed = grant(key, p)
    first = owner.submit(p, signed)
    second = owner.submit(p, signed)  # V009: refused and chronicled
    assert second.status != ATTEMPT_COMMITTED
    found = lookup_outcome(owner.snapshot(), "p1")
    assert found["receipt"]["receipt_digest"] == first.receipt.receipt_digest
    assert found["refused_attempts"] == 1
    assert owner.rows() == {"alpha": "one"}


def test_two_commits_for_one_proposal_id_are_reported_as_inconsistent(owner_and_key):
    owner, key = owner_and_key
    p = proposal()
    owner.submit(p, grant(key, p))
    snapshot = owner.snapshot()
    snapshot["roots"]["AUTHORITY"].append(snapshot["roots"]["AUTHORITY"][-1])
    with pytest.raises(OutcomeError):
        lookup_outcome(snapshot, "p1")


class FakeOwner:
    """Accepts one connection, reads one request, then replies or hangs up."""

    def __init__(self, path, reply=None):
        self.path = str(path)
        self.reply = reply
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.path)
        self.server.listen(1)
        self.server.settimeout(5)
        self.received = None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            conn, _ = self.server.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(5)
            self.received = recv_frame(conn)
            if self.reply is not None:
                conn.sendall(encode_frame(self.reply))

    def close(self):
        self.thread.join(timeout=5)
        self.server.close()


def _sock_dir(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir(mode=0o755)
    return directory


@linux_only
def test_lost_reply_after_sending_is_outcome_unknown_not_refusal(tmp_path):
    fake = FakeOwner(_sock_dir(tmp_path) / "owner.sock")
    client = OwnerClient(fake.path, expected_owner_uid=os.geteuid(), timeout=2)
    try:
        with pytest.raises(OutcomeUnknown):
            client.submit(proposal(), None)
    finally:
        fake.close()
    assert fake.received is not None and fake.received["op"] == "submit"


@linux_only
def test_lost_reply_to_a_read_is_an_error_but_not_outcome_unknown(tmp_path):
    fake = FakeOwner(_sock_dir(tmp_path) / "owner.sock")
    client = OwnerClient(fake.path, expected_owner_uid=os.geteuid(), timeout=2)
    try:
        with pytest.raises(IpcError) as caught:
            client.rows()
    finally:
        fake.close()
    assert not isinstance(caught.value, OutcomeUnknown)


@linux_only
def test_no_owner_is_unavailable_and_nothing_was_sent(tmp_path):
    directory = _sock_dir(tmp_path)
    client = OwnerClient(directory / "owner.sock", expected_owner_uid=os.geteuid(), timeout=2)
    with pytest.raises(OwnerUnavailable):
        client.submit(proposal(), None)
    # A socket file nobody listens on any more (an owner that died) is also unavailable.
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(directory / "owner.sock"))
    stale.close()
    with pytest.raises(OwnerUnavailable):
        client.submit(proposal(), None)


@linux_only
def test_client_reports_a_commit_of_different_content_as_conflict(tmp_path):
    other = proposal(value="two")
    reply = {
        "ok": True,
        "outcome": {
            "status": COMMITTED, "final": True, "proposal_id": "p1", "actor_id": "agent-a",
            "proposal_sha256": proposal_digest(other.to_dict()), "receipt": {"x": 1},
            "refused_attempts": 0,
        },
    }
    fake = FakeOwner(_sock_dir(tmp_path) / "owner.sock", reply=reply)
    client = OwnerClient(fake.path, expected_owner_uid=os.geteuid(), timeout=2)
    try:
        answer = client.outcome(proposal(value="one"))
    finally:
        fake.close()
    assert answer["outcome"]["status"] == CONFLICT
    assert answer["outcome"]["receipt"] is None
