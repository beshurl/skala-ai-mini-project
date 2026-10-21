"""Offline case deletion and restoration with an independent deletion journal.

An old backup is not erased. Controlled restore replays tombstones before use.
This is logical deletion, not guaranteed physical/cryptographic erasure on APFS.
"""
import fcntl
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path

from recase.ledger import append_record, digest, read_ledger
from recase.store import NotFound, Store


@contextmanager
def stopped_database(path):
    path = Path(path).resolve(strict=True)
    lock_path = path.parent / (path.name + ".server.lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("SERVER_RUNNING: stop the server before deletion/maintenance") from None
        yield path


def deletion_events(ledger):
    rows = read_ledger(ledger)  # Missing/corrupt/insecure ledger refuses restore.
    return [e["payload"] for e in rows if e["payload"].get("action") == "delete_case"]


def purge_rows(db, owner, case_id):
    current = db.execute("SELECT owner FROM cases WHERE id=?", (case_id,)).fetchone()
    if current and current[0] != owner:
        raise PermissionError("Deletion owner mismatch")
    db.execute("DELETE FROM events WHERE job_id IN (SELECT id FROM jobs WHERE case_id=? AND owner=?)", (case_id, owner))
    db.execute("DELETE FROM audit WHERE resource IN (SELECT id FROM jobs WHERE case_id=? AND owner=?) OR resource=?", (case_id, owner, case_id))
    db.execute("DELETE FROM jobs WHERE case_id=? AND owner=?", (case_id, owner))
    db.execute("DELETE FROM evidence WHERE case_id=?", (case_id,))
    db.execute("DELETE FROM claims WHERE case_id=?", (case_id,))
    # Schema1 backups remain restorable; schema2 lifecycle metadata is also purged.
    for table in ("case_lifecycle_events", "case_lifecycle"):
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            db.execute(f"DELETE FROM {table} WHERE case_id=?", (case_id,))
    removed = db.execute("DELETE FROM cases WHERE id=? AND owner=?", (case_id, owner)).rowcount
    # Revoke owner sessions as part of deletion; surviving cases require a fresh
    # authenticated operational workflow, not reuse of a backed-up bearer cookie.
    db.execute("DELETE FROM sessions WHERE user_id=?", (owner,))
    return removed


def compact(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA secure_delete=ON")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("VACUUM")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Post-deletion integrity failure")


def delete_case(path, ledger, owner, case_id):
    with stopped_database(path) as path:
        store = Store(path, read_only=True)
        with store.db() as db:
            if not db.execute("SELECT 1 FROM cases WHERE id=? AND owner=?", (case_id, owner)).fetchone():
                raise NotFound()
        # Journal first: a crash between this append and SQL deletion is pending
        # work that apply_deletions replays. Never restore without this journal.
        record = append_record(ledger, {"action": "delete_case", "owner": owner, "case_id": case_id,
                                       "scope": "case/evidence/claims/jobs/events/owner sessions", "policy": "explicit-local-operator-v1"})
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            purge_rows(db, owner, case_id)
            db.execute("INSERT INTO audit(actor,action,resource,created) VALUES(?,?,?,?)",
                       ("local_operator", "case_deleted", digest(case_id), time.time()))
        compact(path)
        return {"status": "PASS", "deletion_record": record["sha256"], "case_digest": digest(case_id),
                "backup_bytes_erased": False, "physical_erasure_verified": False}


def apply_deletions(path, ledger, revoke_all_sessions=True):
    events = deletion_events(ledger)
    if not events and not revoke_all_sessions:
        return {"deleted_cases_replayed": 0, "journal_events": 0, "sessions_revoked": False}
    count = 0
    holds = 0
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA secure_delete=ON")
        db.execute("BEGIN IMMEDIATE")
        for event in events:
            count += purge_rows(db, event["owner"], event["case_id"])
        # Restoring a backup must never revive bearer sessions, including owners
        # unrelated to a tombstone. Historical case content is otherwise preserved.
        if revoke_all_sessions:
            db.execute("DELETE FROM sessions")
            # A backup must not roll back a later hold or revive an old expiry plan.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='case_lifecycle'").fetchone():
                rows = db.execute("SELECT case_id,revision FROM case_lifecycle WHERE hold=0").fetchall()
                for case_id, revision in rows:
                    db.execute("UPDATE case_lifecycle SET hold=1,revision=revision+1 WHERE case_id=?", (case_id,))
                    db.execute("INSERT INTO case_lifecycle_events VALUES(?,?,?,?,?,?)",
                               (case_id, revision + 1, "restore_hold", "local_restore", "Restored data requires a fresh retention review", time.time()))
                holds = len(rows)
    compact(path)
    return {"deleted_cases_replayed": count, "journal_events": len(events), "sessions_revoked": revoke_all_sessions,
            "retention_holds_applied": holds}
