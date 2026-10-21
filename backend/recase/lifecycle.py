"""Explicit lifecycle metadata. Historical timestamps and origin stay unknown."""
import sqlite3
import os
import stat
import time
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path

from recase.ledger import digest, file_digest, utc_now

SCHEMA_VERSION = 2
TABLES = (
    "CREATE TABLE case_lifecycle(case_id TEXT PRIMARY KEY,created REAL,closed REAL,hold INTEGER NOT NULL CHECK(hold IN (0,1)),data_class TEXT NOT NULL CHECK(data_class IN ('synthetic_fixture','unclassified')),revision INTEGER NOT NULL CHECK(revision>=1))",
    "CREATE TABLE case_lifecycle_events(case_id TEXT NOT NULL,revision INTEGER NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,at REAL NOT NULL,PRIMARY KEY(case_id,revision))",
)
CORE_COLUMNS = {
    "sessions": {"token", "user_id", "csrf", "expires"},
    "cases": {"id", "owner", "title", "summary", "version"},
    "evidence": {"id", "case_id", "title", "text", "kind", "attributes", "released_version", "release_order"},
    "claims": {"id", "case_id", "text", "attributes"},
    "jobs": {"id", "case_id", "owner", "version", "status", "snapshot", "result", "error", "model", "created", "updated", "cancel_requested"},
    "events": {"id", "job_id", "type", "payload", "created"},
    "audit": {"id", "actor", "action", "resource", "created"},
}


def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


def case_identity(case_id):
    return digest(["case", case_id])


def private_file(path, expected_uid):
    # Keep migration independent of the streamed operations worker module.
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != expected_uid or stat.S_IMODE(info.st_mode) != 0o600:
        raise PermissionError("Private operator-owned regular database required")
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError("Symlink ancestors refused")
    return info


def migrate_v1(path, backup):
    """Back up a stopped v1 DB before a transactional v2 migration; never infer dates."""
    from recase.retention import stopped_database
    from recase.store import Store
    path, backup = Path(path).absolute(), Path(backup).absolute()
    private_file(path, os.geteuid())
    if path.stat().st_nlink != 1 or backup == path or backup.is_symlink() or any(p.is_symlink() for p in backup.parents):
        raise ValueError("Independent regular database and new backup path required")
    with stopped_database(path):
        source = Store(path, read_only=True)
        with source.db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                return {"status": "ALREADY_CURRENT", "schema_version": version, "migration_executed": False}
            if version != 1 or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Healthy schema1 database required")
            for table, expected in CORE_COLUMNS.items():
                if {row[1] for row in db.execute(f"PRAGMA table_info({table})")} != expected:
                    raise ValueError("Known RECASE schema1 column contract required")
            if db.execute("SELECT 1 FROM sqlite_master WHERE name IN ('case_lifecycle','case_lifecycle_events')").fetchone():
                raise ValueError("Unexpected lifecycle tables in schema1; inspect without mutation")
        # Failure after backup leaves the original rollback point intact.
        source.backup(backup)
        backup_sha = file_digest(backup)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise RuntimeError("Schema changed during migration")
            for statement in TABLES:
                db.execute(statement)
            db.execute("INSERT INTO case_lifecycle SELECT id,NULL,NULL,0,'unclassified',1 FROM cases")
            db.execute("PRAGMA user_version=2")
        return {"status": "PASS", "schema_version": SCHEMA_VERSION, "migration_executed": True,
                "rollback_backup_sha256": backup_sha, "historical_dates_inferred": 0,
                "historical_cases_reclassified_synthetic": 0}


def state(db, owner, case_id):
    from recase.store import NotFound
    row = db.execute("SELECT l.*,c.version AS evidence_version FROM cases c JOIN case_lifecycle l ON l.case_id=c.id WHERE c.id=? AND c.owner=?",
                     (case_id, owner)).fetchone()
    if row is None:
        raise NotFound()
    return {"case_id": case_id, "created_at": timestamp(row["created"]), "closed_at": timestamp(row["closed"]),
            "hold": bool(row["hold"]), "data_class": row["data_class"], "revision": row["revision"],
            "evidence_version": row["evidence_version"]}


def transition(db, owner, case_id, expected_version, expected_revision, action, reason):
    from recase.store import Conflict, NotFound
    if action not in {"close", "reopen", "hold", "release_hold"} or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise ValueError("Explicit lifecycle action and reason required")
    case = db.execute("SELECT version FROM cases WHERE id=? AND owner=?", (case_id, owner)).fetchone()
    if case is None:
        raise NotFound()
    before = state(db, owner, case_id)
    if type(expected_version) is not int or case[0] != expected_version:
        raise Conflict("EVIDENCE_VERSION_CHANGED")
    if type(expected_revision) is not int or before["revision"] != expected_revision:
        raise Conflict("LIFECYCLE_REVISION_CHANGED")
    if action == "close" and db.execute("SELECT 1 FROM jobs WHERE case_id=? AND status IN ('QUEUED','RUNNING')", (case_id,)).fetchone():
        raise Conflict("CASE_HAS_ACTIVE_JOB")
    changed = {"close": before["closed_at"] is None, "reopen": before["closed_at"] is not None,
               "hold": not before["hold"], "release_hold": before["hold"]}[action]
    if not changed:
        return before  # Repeated close must not reset the retention deadline.
    now, revision = time.time(), before["revision"] + 1
    if action == "close" and before["created_at"] is not None and now < datetime.fromisoformat(before["created_at"]).timestamp():
        raise Conflict("CLOCK_BEFORE_CASE_CREATION")
    if action in {"close", "reopen"}:
        db.execute("UPDATE case_lifecycle SET closed=?,revision=? WHERE case_id=?", (now if action == "close" else None, revision, case_id))
    else:
        db.execute("UPDATE case_lifecycle SET hold=?,revision=? WHERE case_id=?", (int(action == "hold"), revision, case_id))
    db.execute("INSERT INTO case_lifecycle_events VALUES(?,?,?,?,?,?)", (case_id, revision, action, owner, reason.strip(), now))
    db.execute("INSERT INTO audit(actor,action,resource,created) VALUES(?,?,?,?)",
               (owner, "case_" + action, case_id, now))
    return state(db, owner, case_id)


def require_open(db, owner, case_id):
    from recase.store import Conflict
    if state(db, owner, case_id)["closed_at"] is not None:
        raise Conflict("CASE_CLOSED")


def inventory(path):
    """Read a consistent inventory containing no titles, text, owners or sessions."""
    from recase.store import Store
    with Store(path, read_only=True).db() as db:
        db.execute("BEGIN")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in {1, SCHEMA_VERSION}:
            raise ValueError("Supported case database schema required")
        if version == 1:
            values = [{"id": row[0], "created": None, "closed": None, "hold": 0,
                       "data_class": "unclassified", "revision": None} for row in db.execute("SELECT id FROM cases LIMIT 1001")]
        else:
            values = [dict(row) for row in db.execute("SELECT c.id,l.created,l.closed,l.hold,l.data_class,l.revision FROM cases c LEFT JOIN case_lifecycle l ON l.case_id=c.id ORDER BY c.id LIMIT 1001")]
        if len(values) > 1000:
            raise ValueError("Retention inventory limit1000 cases")
    cases = [{"identity_sha256": case_identity(row["id"]),
            "created_at": timestamp(row["created"]), "closed_at": timestamp(row["closed"]),
            "hold": row["hold"] != 0, "data_class": row["data_class"] or "unclassified",
            "lifecycle_revision": row["revision"]} for row in values]
    return {"schema_version": version, "captured_at": utc_now(), "case_state_sha256": digest(cases), "cases": cases, "backups": [],
            "scope": "metadata_only_not_a_deletion_plan", "deletions_executed": 0}
