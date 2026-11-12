"""WEAVER-V008 first-slice acceptance tests: owner and requesters under distinct real uids.

These start the owner as uid 61001 and attack it from uids 61002 (the listed requester) and
61003 (an unlisted local user). They need root to switch uids, so they are skipped for
ordinary users. A green ordinary run therefore says NOTHING about these properties. The
`v008-isolation` workflow sets WEAVER_REQUIRE_ISOLATION=1, which turns the skip into a
failure so a missing root context cannot pass silently.

Declared attacker model: an unprivileged local user on the same host who can run any code
as their own uid and knows every path and the protocol. Out of scope: root, the owner uid,
kernel bugs, hardware, and a compromised trusted launcher.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from weaver_contracts.canonical import canonicalize
from weaver_contracts.gate import Proposal
from weaver_runtime.gate import COMMITTED, REJECTED
from weaver_runtime.owner_ipc import UntrustedPathError, assert_trusted_path
from weaver_runtime.protected_write import GRANT_DOMAIN

OWNER_UID, REQUESTER_UID, OTHER_UID = 61001, 61002, 61003
SECOND_PEER_UID = 61004  # listed, but may speak only for agent-b
REPO = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux SO_PEERCRED and /proc"
)


def _public_raw(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


def make_proposal(pid="p1", key="alpha", value="one", actor="agent-a"):
    return Proposal(pid, actor, "WRITE_KEY", "policy-v1", {"key": key, "value": value})


def make_grant(key, proposal, *, grant_id="grant-1"):
    now = int(time.time())
    fields = {
        "issuer_id": "issuer-a",
        "audience": "weaver-vertical-001",
        "grant_id": grant_id,
        "proposal_sha256": hashlib.sha256(canonicalize(proposal.to_dict())).hexdigest(),
        "valid_from": now - 60,
        "valid_until": now + 600,
    }
    signature = key.sign(GRANT_DOMAIN + canonicalize(fields))
    return {
        "grant": fields,
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
    }


SUBMIT = """
import json, sys
from weaver_runtime.owner_ipc import OwnerClient
req = json.loads(sys.argv[1])
client = OwnerClient(req["socket"], expected_owner_uid=req["owner_uid"],
                     verify_path=req.get("verify_path", True),
                     timeout=req.get("timeout", 5.0))
try:
    reply = getattr(client, req["op"])(*req.get("args", []))
    print(json.dumps({"reply": reply}))
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}))
"""


class Deployment:
    def __init__(self) -> None:
        if os.geteuid() != 0:
            message = "needs root to run the owner and attackers under distinct uids"
            if os.environ.get("WEAVER_REQUIRE_ISOLATION") == "1":
                pytest.fail(message + " (WEAVER_REQUIRE_ISOLATION=1)")
            pytest.skip(message)
        self.key = Ed25519PrivateKey.generate()
        self.base = Path(tempfile.mkdtemp(prefix="weaver-v008-", dir="/tmp"))
        os.chmod(self.base, 0o755)  # root-owned, traversable by every uid
        self.code = self.base / "code"
        for package in ("contracts", "runtime", "verifier"):
            shutil.copytree(
                REPO / "packages" / package,
                self.code / package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        self._run_chmod(self.code, "a+rX")
        self.data = self._make_dir("owner-data", OWNER_UID, 0o700)
        self.run = self._make_dir("run", OWNER_UID, 0o755)
        self.conf = self._make_dir("conf", OWNER_UID, 0o700)
        self.sock = self.run / "owner.sock"
        self.config_path = self.conf / "owner.json"
        self.config = {
            "data_dir": str(self.data),
            "socket_path": str(self.sock),
            "issuer_id": "issuer-a",
            "allowed_keys": ["alpha", "beta"],
            "trusted_public_key_b64": base64.b64encode(_public_raw(self.key)).decode(),
            "peers": {str(REQUESTER_UID): ["agent-a"], str(SECOND_PEER_UID): ["agent-b"]},
        }
        self.write_config()
        self.proc: subprocess.Popen[str] | None = None
        self.extra: list[subprocess.Popen[str]] = []  # further owners on the same store
        self.leaks: list[int] = []

    def _run_chmod(self, path: Path, mode: str) -> None:
        subprocess.run(["chmod", "-R", mode, str(path)], check=True)

    def _make_dir(self, name: str, uid: int, mode: int) -> Path:
        path = self.base / name
        path.mkdir()
        os.chown(path, uid, uid)
        os.chmod(path, mode)
        return path

    def write_config(self, *, mode: int = 0o600, uid: int = OWNER_UID) -> None:
        self.write_config_file(self.config_path, self.config, mode=mode, uid=uid)

    @staticmethod
    def write_config_file(path: Path, config: dict, *, mode: int = 0o600, uid: int = OWNER_UID):
        path.write_text(json.dumps(config))
        os.chown(path, uid, uid)
        os.chmod(path, mode)

    def env(self) -> dict[str, str]:
        roots = [self.code / name for name in ("contracts", "runtime", "verifier")]
        return {
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": os.pathsep.join(map(str, roots)),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": "/nonexistent",
        }

    def popen_owner(
        self,
        *,
        uid: int | None = OWNER_UID,
        pass_fds=(),
        failpoint: str | None = None,
        config_path: Path | None = None,
    ):
        # uid=None launches as the current user (root here), with no uid or group change.
        env = self.env()
        if failpoint is not None:
            env["WEAVER_OWNER_FAILPOINT"] = failpoint
        config = str(config_path or self.config_path)
        return subprocess.Popen(
            [sys.executable, "-m", "weaver_runtime.owner_main", "--config", config],
            env=env, cwd="/", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, pass_fds=pass_fds,
            user=uid, group=uid, extra_groups=None if uid is None else [],
        )

    @staticmethod
    def await_ready(proc: subprocess.Popen[str]) -> int:
        assert proc.stdout is not None and proc.stderr is not None
        deadline = time.time() + 15
        while time.time() < deadline:
            ready, _, _ = select.select([proc.stdout], [], [], 0.2)
            if ready:
                line = proc.stdout.readline().strip()
                assert line == "READY", line
                return proc.pid
            if proc.poll() is not None:
                raise AssertionError(f"owner exited early: {proc.stderr.read()}")
        raise AssertionError("owner did not become ready")

    def start_owner(self, failpoint: str | None = None) -> int:
        self.stop()  # reap any earlier owner process before starting a new one
        self.proc = self.popen_owner(failpoint=failpoint)
        return self.await_ready(self.proc)

    def start_extra_owner(self, config_path: Path) -> subprocess.Popen[str]:
        """A further owner process on the SAME store, serving its own socket."""
        proc = self.popen_owner(config_path=config_path)
        self.extra.append(proc)
        self.await_ready(proc)
        return proc

    def refused_start(self, **kwargs) -> subprocess.CompletedProcess:
        proc = self.popen_owner(**kwargs)
        try:
            _out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise AssertionError("owner started when it should have refused") from None
        return subprocess.CompletedProcess(proc.args, proc.returncode, "", err)

    def run_as(self, uid: int, code: str, *args: str, timeout: int = 30):
        return subprocess.run(
            [sys.executable, "-c", code, *args],
            user=uid, group=uid, extra_groups=[], env=self.env(), cwd="/",
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
            check=False,
        )

    def call(
        self, uid: int, op: str, *args, socket_path=None, verify_path=True, timeout=5.0
    ) -> dict:
        request = {
            "socket": str(socket_path or self.sock), "owner_uid": OWNER_UID, "op": op,
            "args": list(args), "verify_path": verify_path, "timeout": timeout,
        }
        done = self.run_as(uid, SUBMIT, json.dumps(request))
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    def submit(self, uid, proposal, signed_grant, **kwargs) -> dict:
        return self.call(uid, "submit", proposal.to_dict(), signed_grant, **kwargs)

    def rows(self) -> dict:
        return self.call(REQUESTER_UID, "rows")["reply"]["rows"]

    def wait_for_owner_exit(self, timeout: float = 15) -> int:
        assert self.proc is not None
        return self.proc.wait(timeout=timeout)

    @staticmethod
    def terminate(proc: subprocess.Popen[str] | None) -> None:
        if proc is not None and proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if proc is not None:
            for stream in (proc.stdout, proc.stderr):
                if stream:
                    stream.close()

    def stop(self) -> None:
        self.terminate(self.proc)

    def cleanup(self) -> None:
        self.stop()
        for proc in self.extra:
            self.terminate(proc)
        shutil.rmtree(self.base, ignore_errors=True)


@pytest.fixture
def dep():
    deployment = Deployment()
    try:
        yield deployment
    finally:
        deployment.cleanup()


@pytest.fixture
def live(dep):
    dep.pid = dep.start_owner()
    return dep


def committed_write(live, pid="p1", key="alpha", value="one"):
    proposal = make_proposal(pid, key, value)
    reply = live.submit(REQUESTER_UID, proposal, make_grant(live.key, proposal, grant_id=pid))
    assert reply["reply"]["ok"] and reply["reply"]["status"] == COMMITTED, reply
    return reply["reply"]


def test_owner_runs_as_its_own_uid_and_is_marked_non_dumpable(live):
    status = Path(f"/proc/{live.pid}/status").read_text()
    uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
    assert [int(part) for part in uid_line.split()[1:]] == [OWNER_UID] * 4
    # dumpable=0 makes the kernel hand the files inside /proc/<pid> (not the directory
    # itself) to root. A control process under the same uid that never cleared the flag
    # shows the check discriminates.
    control = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        user=OWNER_UID, group=OWNER_UID, extra_groups=[], env=live.env(), cwd="/",
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        assert os.stat(f"/proc/{control.pid}/environ").st_uid == OWNER_UID
        assert os.stat(f"/proc/{live.pid}/environ").st_uid == 0
        assert os.stat(f"/proc/{live.pid}/fd").st_uid == 0
    finally:
        control.kill()
        control.wait()


def test_owner_refuses_to_run_as_root(dep):
    done = dep.refused_start(uid=None)
    assert done.returncode == 2
    assert "root" in done.stderr


def test_signed_write_commits_through_the_socket_and_replays(live):
    reply = committed_write(live)
    assert reply["receipt"]["event_type"] == "EXECUTION_COMMITTED"
    assert live.rows() == {"alpha": "one"}
    anchor = live.call(REQUESTER_UID, "anchor")["reply"]["anchor"]
    live.stop()
    # A fresh process, as the owner uid, replays the history the service wrote.
    code = """
import json, sqlite3, sys
from weaver_runtime.ledger import ReceiptLedger
from weaver_verifier.protected_write import verify_protected_write
data = json.loads(sys.argv[1])
with ReceiptLedger(data["path"], ledger_id="weaver-vertical-001") as ledger:
    snapshot = ledger.snapshot()
with sqlite3.connect(data["path"]) as conn:
    rows = dict(conn.execute("SELECT key, value FROM protected_kv"))
result = verify_protected_write(snapshot, rows, anchor=data["anchor"])
print("PASS" if result.ok and result.anchored else result.reason)
"""
    done = live.run_as(
        OWNER_UID, code, json.dumps({"path": str(live.data / "owner.db"), "anchor": anchor})
    )
    assert done.stdout.strip() == "PASS", done.stderr


def test_requester_uid_cannot_read_or_write_the_database_or_wal(live):
    committed_write(live)
    script = """
import json, os, sqlite3, sys
d = sys.argv[1]
out = {}
def attempt(name, fn):
    try:
        fn()
        out[name] = "ALLOWED"
    except (PermissionError, sqlite3.OperationalError) as exc:
        out[name] = type(exc).__name__
for f in ("owner.db", "owner.db-wal", "owner.db-shm"):
    attempt("read " + f, lambda f=f: open(os.path.join(d, f), "rb").read(1))
    attempt("append " + f, lambda f=f: open(os.path.join(d, f), "ab").write(b"x"))
attempt("list", lambda: os.listdir(d))
attempt("create", lambda: open(os.path.join(d, "evil"), "w").write("x"))
attempt("sqlite", lambda: sqlite3.connect(os.path.join(d, "owner.db")).execute(
    "INSERT INTO protected_kv VALUES('alpha','bypass','untrusted')"))
attempt("rename directory", lambda: os.rename(d, d + ".moved"))
attempt("veto flag", lambda: open(os.path.join(d, "veto.flag"), "w").write("x"))
print(json.dumps(out))
"""
    done = live.run_as(REQUESTER_UID, script, str(live.data))
    outcomes = json.loads(done.stdout)
    assert outcomes and "ALLOWED" not in outcomes.values(), outcomes
    assert not (live.data / "evil").exists()
    assert live.rows() == {"alpha": "one"}


def test_the_original_v008_bypass_script_is_denied_by_the_os(live):
    bypass = (
        "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
        "c.execute(\"INSERT INTO protected_kv VALUES('alpha','bypass','untrusted')\"); "
        "c.commit()"
    )
    done = live.run_as(REQUESTER_UID, bypass, str(live.data / "owner.db"))
    assert done.returncode != 0
    assert live.rows() == {}


def test_valid_grant_from_an_unlisted_uid_is_refused_and_owner_keeps_serving(live):
    proposal = make_proposal()
    grant = make_grant(live.key, proposal)
    reply = live.submit(OTHER_UID, proposal, grant)
    assert "error" in reply and "reply" not in reply, reply
    assert live.rows() == {}
    committed_write(live, pid="p2")  # still serving the listed uid afterwards
    assert live.rows() == {"alpha": "one"}


def test_listed_uid_cannot_speak_for_an_unlisted_actor(live):
    proposal = make_proposal(actor="agent-b")
    reply = live.submit(REQUESTER_UID, proposal, make_grant(live.key, proposal))
    assert reply["reply"] == {"ok": False, "error": "actor-not-permitted"}
    assert live.rows() == {}


def test_grant_signed_by_a_key_the_owner_does_not_trust_is_rejected(live):
    proposal = make_proposal()
    forged = make_grant(Ed25519PrivateKey.generate(), proposal)
    reply = live.submit(REQUESTER_UID, proposal, forged)["reply"]
    assert reply["ok"] and reply["status"] == REJECTED
    assert live.rows() == {}


def test_veto_flag_in_the_private_directory_blocks_the_effect(live):
    (live.data / "veto.flag").write_text("hold")
    proposal = make_proposal()
    reply = live.submit(REQUESTER_UID, proposal, make_grant(live.key, proposal))["reply"]
    assert reply.get("status") != COMMITTED, reply
    assert live.rows() == {}


ATTACKER = """
import os, socket, sys
path, record = sys.argv[1], sys.argv[2]
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(path)
os.chmod(path, 0o666)  # a spoofer wants victims to be able to connect
server.listen(1)
print("READY", flush=True)
server.settimeout(10)
received = -1
try:
    conn, _ = server.accept()
    conn.settimeout(1)
    try:
        received = len(conn.recv(65536))
    except OSError:
        received = 0
except OSError:
    pass
open(record, "w").write(str(received))
"""


def _start_attacker(dep, directory: Path):
    record = directory / "received"
    proc = subprocess.Popen(
        [sys.executable, "-c", ATTACKER, str(directory / "owner.sock"), str(record)],
        user=OTHER_UID, group=OTHER_UID, extra_groups=[], env=dep.env(), cwd="/",
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert proc.stdout is not None and proc.stderr is not None
    assert proc.stdout.readline().strip() == "READY", proc.stderr.read()
    return proc, record


def _attacker_dir(dep) -> Path:
    path = dep.base / "attacker"
    path.mkdir()
    os.chown(path, OTHER_UID, OTHER_UID)
    os.chmod(path, 0o755)
    return path


def test_client_refuses_a_socket_in_a_directory_an_attacker_controls(dep):
    directory = _attacker_dir(dep)
    proc, _record = _start_attacker(dep, directory)
    try:
        reply = dep.submit(
            REQUESTER_UID, make_proposal(), None, socket_path=directory / "owner.sock"
        )
    finally:
        proc.kill()
        proc.communicate()
    assert reply["error"] == "UntrustedPathError", reply


def test_client_sends_nothing_to_a_server_running_as_the_wrong_uid(dep):
    directory = _attacker_dir(dep)
    proc, record = _start_attacker(dep, directory)
    try:
        proposal = make_proposal()
        reply = dep.submit(
            REQUESTER_UID, proposal, make_grant(dep.key, proposal),
            socket_path=directory / "owner.sock", verify_path=False,
        )
        proc.wait(timeout=15)
    finally:
        proc.kill()
        proc.communicate()
    assert reply["error"] == "PeerIdentityError", reply
    assert record.read_text() == "0", "the spoofed server must receive zero bytes"


def test_requester_cannot_replace_or_remove_the_socket(live):
    script = """
import json, os, sys
d = sys.argv[1]
out = {}
def attempt(name, fn):
    try:
        fn()
        out[name] = "ALLOWED"
    except PermissionError:
        out[name] = "PermissionError"
attempt("unlink socket", lambda: os.unlink(os.path.join(d, "owner.sock")))
attempt("symlink beside", lambda: os.symlink("/tmp", os.path.join(d, "evil")))
attempt("rename socket", lambda: os.rename(os.path.join(d, "owner.sock"),
                                           os.path.join(d, "moved")))
attempt("rename run dir", lambda: os.rename(d, d + ".moved"))
print(json.dumps(out))
"""
    outcomes = json.loads(live.run_as(REQUESTER_UID, script, str(live.run)).stdout)
    assert "ALLOWED" not in outcomes.values(), outcomes
    committed_write(live)


def test_symlinked_leaf_or_ancestor_is_refused_by_the_path_check(dep):
    dep.start_owner()
    (dep.base / "link-sock").symlink_to(dep.sock)
    (dep.base / "link-run").symlink_to(dep.run)
    with pytest.raises(UntrustedPathError, match="symlink"):
        assert_trusted_path(dep.base / "link-sock", OWNER_UID, leaf="socket")
    with pytest.raises(UntrustedPathError, match="symlink"):
        assert_trusted_path(dep.base / "link-run" / "owner.sock", OWNER_UID, leaf="socket")
    assert_trusted_path(dep.sock, OWNER_UID, leaf="socket")


def test_owner_refuses_a_symlinked_data_directory(dep):
    (dep.base / "link-data").symlink_to(dep.data)
    dep.config["data_dir"] = str(dep.base / "link-data")
    dep.write_config()
    done = dep.refused_start()
    assert done.returncode == 2 and "symlink" in done.stderr


def test_owner_refuses_a_database_file_it_does_not_own(dep):
    db = dep.data / "owner.db"
    db.write_text("")
    os.chown(db, REQUESTER_UID, REQUESTER_UID)
    os.chmod(db, 0o600)
    done = dep.refused_start()
    assert done.returncode == 2 and "private regular file" in done.stderr


def test_owner_refuses_a_socket_directory_others_can_write(dep):
    os.chmod(dep.run, 0o777)
    done = dep.refused_start()
    assert done.returncode == 2 and "mode" in done.stderr


def test_owner_refuses_a_data_directory_others_can_enter(dep):
    os.chmod(dep.data, 0o755)
    done = dep.refused_start()
    assert done.returncode == 2 and "mode" in done.stderr
    # The launcher's own check must be the one that refuses. The edge-telemetry recorder
    # also refuses a non-private directory, as a second layer; if the launcher's check were
    # removed, that layer would still refuse and this test would pass without noticing.
    assert "edge telemetry" not in done.stderr, done.stderr


def test_owner_refuses_to_start_with_an_inherited_descriptor(dep):
    leak = os.open(dep.base / "leaked", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        done = dep.refused_start(pass_fds=(leak,))
    finally:
        os.close(leak)
    assert done.returncode == 2 and "inherited file descriptors" in done.stderr


def test_a_normal_launch_holds_only_expected_descriptors(live):
    allowed_prefixes = (str(live.data), "pipe:", "socket:", "/dev/null", "anon_inode:")
    targets = [
        os.readlink(f"/proc/{live.pid}/fd/{name}") for name in os.listdir(f"/proc/{live.pid}/fd")
    ]
    assert targets
    unexpected = [t for t in targets if not t.startswith(allowed_prefixes)]
    assert not unexpected, unexpected


def test_requester_cannot_trace_inspect_or_signal_the_owner(live):
    script = """
import ctypes, json, os, signal, sys
pid = int(sys.argv[1])
out = {}
def attempt(name, fn):
    try:
        fn()
        out[name] = "ALLOWED"
    except PermissionError:
        out[name] = "PermissionError"
attempt("read mem", lambda: open(f"/proc/{pid}/mem", "rb").read(1))
attempt("read environ", lambda: open(f"/proc/{pid}/environ", "rb").read(1))
attempt("list fds", lambda: os.listdir(f"/proc/{pid}/fd"))
attempt("kill", lambda: os.kill(pid, signal.SIGKILL))
libc = ctypes.CDLL(None, use_errno=True)
result = libc.ptrace(16, pid, 0, 0)  # PTRACE_ATTACH
out["ptrace"] = [result, ctypes.get_errno()]
print(json.dumps(out))
"""
    outcomes = json.loads(live.run_as(REQUESTER_UID, script, str(live.pid)).stdout)
    assert outcomes.pop("ptrace") == [-1, 1], "PTRACE_ATTACH must fail with EPERM"
    assert "ALLOWED" not in outcomes.values(), outcomes
    assert live.proc.poll() is None
    committed_write(live)


@pytest.mark.parametrize(
    ("label", "mode", "uid"),
    [("group-writable", 0o620, OWNER_UID), ("owned-by-requester", 0o600, REQUESTER_UID)],
)
def test_owner_refuses_a_substituted_or_loosened_config(dep, label, mode, uid):
    dep.write_config(mode=mode, uid=uid)
    done = dep.refused_start()
    assert done.returncode == 2, label
    assert "refused to start" in done.stderr


def test_owner_refuses_a_config_with_unknown_fields(dep):
    dep.config["extra_trusted_key"] = "x"
    dep.write_config()
    done = dep.refused_start()
    assert done.returncode == 2 and "unknown fields" in done.stderr


def test_requester_cannot_write_the_config_or_the_code(live):
    script = """
import json, os, sys
out = {}
for name, path in (("config", sys.argv[1]), ("code", sys.argv[2])):
    try:
        open(path, "ab").write(b"x")
        out[name] = "ALLOWED"
    except PermissionError:
        out[name] = "PermissionError"
print(json.dumps(out))
"""
    code_file = live.code / "runtime" / "weaver_runtime" / "owner_main.py"
    done = live.run_as(REQUESTER_UID, script, str(live.config_path), str(code_file))
    assert json.loads(done.stdout) == {"config": "PermissionError", "code": "PermissionError"}
