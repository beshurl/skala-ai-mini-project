"""Private account snapshots and cooperative maintenance locks. No account restore."""
import fcntl
import math
import os
import re
import sqlite3
import stat
import time
from contextlib import closing, contextmanager
from pathlib import Path

from recase.encrypted_backups import absolute_path, read_private
from recase.ledger import digest

ACCOUNT_COLUMNS = ["id", "email", "name", "password_hash", "role", "enabled", "credential_version", "created"]
MAX_ACCOUNT_BYTES = 8 * 1024 * 1024
ACCOUNT_TABLE_SQL = "CREATE TABLE accounts(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','admin')),enabled INTEGER NOT NULL DEFAULT 1,credential_version INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL)"


@contextmanager
def account_lock(path, exclusive=False):
    path = absolute_path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise PermissionError("ACCOUNT_SYMLINK_REFUSED")
    lock = path.with_name(path.name + ".maintenance.lock")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+b") as stream:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size):
            raise PermissionError("PRIVATE_ACCOUNT_LOCK_REQUIRED")
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("ACCOUNT_MAINTENANCE_BUSY") from None
        yield


def account_snapshot(path, versions=(1,)):
    """Read a bounded, consistent account image; caller holds the account lock."""
    path = absolute_path(path)
    # Validate metadata without reading unbounded data or following symlinks.
    info = path.lstat()
    if info.st_size > MAX_ACCOUNT_BYTES:
        raise ValueError("ACCOUNT_SNAPSHOT_BUDGET_EXCEEDED")
    read_private(path, MAX_ACCOUNT_BYTES)
    deadline = time.monotonic() + 10
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as source, closing(sqlite3.connect(":memory:")) as db:
        page_size = source.execute("PRAGMA page_size").fetchone()[0]
        def progress(status, remaining, total):
            if total * page_size > MAX_ACCOUNT_BYTES or time.monotonic() > deadline:
                raise RuntimeError("ACCOUNT_SNAPSHOT_BUDGET_EXCEEDED")
        source.backup(db, pages=256, progress=progress, sleep=.01)
        db.row_factory = sqlite3.Row
        rows = read_account_rows(db, versions)
        image = db.serialize()
        if len(image) > MAX_ACCOUNT_BYTES:
            raise ValueError("ACCOUNT_SNAPSHOT_BUDGET_EXCEEDED")
    after = path.lstat()
    if (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino):
        raise RuntimeError("ACCOUNT_DATABASE_REPLACED")
    return image, rows, digest(rows)


def validate_owners(data, rows):
    """Disabled accounts retain ownership; never grant ownership by email/order."""
    users = {r["id"] for r in rows}
    cases = {r["id"]: r["owner"] for r in data["cases"]}
    if any(owner not in users for owner in cases.values()):
        raise ValueError("UNMAPPED_LEGACY_OR_MISSING_ACCOUNT_OWNER")
    if any(r["owner"] != cases.get(r["case_id"]) for r in data["jobs"]):
        raise ValueError("JOB_ACCOUNT_OWNER_MISMATCH")
    return {"cases_with_current_account": len(cases), "jobs_with_matching_owner": len(data["jobs"])}


def read_account_rows(db, versions=(1,)):
    """Validate known schema and bounded credential rows; do not export rows."""
    if (db.execute("PRAGMA user_version").fetchone()[0] not in versions
            or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} != {"accounts"}
            or [r[1] for r in db.execute("PRAGMA table_info(accounts)")] != ACCOUNT_COLUMNS
            or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone()):
        raise ValueError("KNOWN_ACCOUNT_SCHEMA_REQUIRED")
    rows = [dict(r) for r in db.execute("SELECT * FROM accounts ORDER BY id LIMIT 10001")]
    if len(rows) > 10000:
        raise ValueError("ACCOUNT_SNAPSHOT_BUDGET_EXCEEDED")
    for row in rows:
        if (not isinstance(row["id"], str) or not re.fullmatch(r"USER-[0-9a-f]{32}", row["id"])
                or not isinstance(row["email"], str) or not 3 <= len(row["email"]) <= 254
                or not isinstance(row["name"], str) or not 1 <= len(row["name"]) <= 40
                or not isinstance(row["password_hash"], str)
                or not re.fullmatch(r"scrypt\$32768\$8\$3\$[0-9a-f]{32}\$[0-9a-f]{64}", row["password_hash"])
                or row["role"] not in {"user", "admin"} or row["enabled"] not in {0, 1}
                or type(row["credential_version"]) is not int or row["credential_version"] < 1
                or not isinstance(row["created"], (int, float)) or not math.isfinite(row["created"])):
            raise ValueError("KNOWN_ACCOUNT_ROW_REQUIRED")
    if len({r["id"] for r in rows}) != len(rows) or len({r["email"] for r in rows}) != len(rows):
        raise ValueError("DUPLICATE_ACCOUNT_IDENTITIES")
    return rows


def portable_account_image(rows):
    """Rebuild known rows via SQLite APIs, never patch WAL image headers."""
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute(ACCOUNT_TABLE_SQL)
        db.executemany("INSERT INTO accounts VALUES(?,?,?,?,?,?,?,?)", [[r[k] for k in ACCOUNT_COLUMNS] for r in rows])
        db.execute("PRAGMA user_version=1")
        db.commit()
        db.row_factory = sqlite3.Row
        if digest(read_account_rows(db)) != digest(rows):
            raise RuntimeError("PORTABLE_ACCOUNT_IMAGE_MISMATCH")
        result = db.serialize()
        if len(result) > MAX_ACCOUNT_BYTES:
            raise ValueError("ACCOUNT_SNAPSHOT_BUDGET_EXCEEDED")
        return result
