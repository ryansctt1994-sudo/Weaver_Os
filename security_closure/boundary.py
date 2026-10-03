"""Trusted approval store and atomic SQLite actuator; no external-effect guarantee."""

import hashlib
import json
import secrets
import sqlite3
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Request:
    actor: str
    action: str
    resource: str
    amount: int
    nonce: str

    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


class Boundary:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY, value INTEGER);
                CREATE TABLE IF NOT EXISTS grants(
                    id TEXT PRIMARY KEY, subject TEXT, resource TEXT, parent TEXT,
                    expires INTEGER, revoked INTEGER);
                CREATE TABLE IF NOT EXISTS approvals(
                    token TEXT PRIMARY KEY, digest TEXT, expires INTEGER, used INTEGER);
                CREATE TABLE IF NOT EXISTS receipts(
                    seq INTEGER PRIMARY KEY, digest TEXT, verdict TEXT, reason TEXT,
                    before_value INTEGER, after_value INTEGER);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def bootstrap(self):
        """Trusted setup only; never exposed to agent content or tool dispatch."""
        with self.connect() as db:
            db.execute("INSERT INTO resources VALUES('counter', 0)")
            db.execute("INSERT INTO grants VALUES('root','owner','counter',NULL,100,0)")
            db.execute("INSERT INTO grants VALUES('leaf','agent','counter','root',90,0)")

    def approve(self, request, expires=80):
        """Trusted human-side adapter: possession alone is not actor authentication."""
        token = secrets.token_hex(32)
        with self.connect() as db:
            db.execute("INSERT INTO approvals VALUES(?,?,?,0)", (token, request.digest(), expires))
        return token

    def snapshot(self):
        with self.connect() as db:
            return db.execute("SELECT id,value FROM resources ORDER BY id").fetchall()

    def lineage_valid(self, db, grant_id, request, now):
        seen = set()
        first = True
        while grant_id:
            if grant_id in seen:
                return False
            seen.add(grant_id)
            row = db.execute("SELECT * FROM grants WHERE id=?", (grant_id,)).fetchone()
            if not row:
                return False
            gid, subject, resource, parent, expires, revoked = row
            if revoked or now >= expires or resource != request.resource:
                return False
            if first and subject != request.actor:
                return False
            if parent is None:
                return gid == "root" and subject == "owner"
            first = False
            grant_id = parent
        return False

    def execute(self, request, token, principal, now=2, grant="leaf", crash=None):
        """Principal is supplied by a trusted authentication adapter, never the model.

        Effect, approval consumption and receipt share one transaction. Injected
        crashes exercise rollback and post-commit uncertainty; no network/file tool
        is executed inside this bounded actuator.
        """
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            before = db.execute(
                "SELECT value FROM resources WHERE id=?", (request.resource,)
            ).fetchone()
            before = before[0] if before else None
            approval = db.execute(
                "SELECT digest,expires,used FROM approvals WHERE token=?", (token,)
            ).fetchone()
            reason = None
            if principal != request.actor:
                reason = "identity"
            elif request.action != "increment" or type(request.amount) is not int:
                reason = "schema"
            elif not 1 <= request.amount <= 5 or before is None:
                reason = "scope"
            elif not approval or approval[0] != request.digest():
                reason = "binding"
            elif now >= approval[1] or approval[2]:
                reason = "replay_or_expiry"
            elif not self.lineage_valid(db, grant, request, now):
                reason = "lineage"
            verdict = "REJECT" if reason else "ACCEPT"
            after = before
            if verdict == "ACCEPT":
                after = before + request.amount
                db.execute("UPDATE resources SET value=? WHERE id=?", (after, request.resource))
                if crash == "before_commit":
                    raise RuntimeError("injected pre-commit crash")
                db.execute("UPDATE approvals SET used=1 WHERE token=?", (token,))
            db.execute(
                "INSERT INTO receipts(digest,verdict,reason,before_value,after_value) "
                "VALUES(?,?,?,?,?)",
                (request.digest(), verdict, reason, before, after),
            )
            db.commit()
            if crash == "after_commit":
                raise RuntimeError("injected post-commit crash")
            return verdict
