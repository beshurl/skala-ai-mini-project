"""Local append-only, hash-chained records; not an OS/identity trust boundary."""
import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def locked_records(path, create=False):
    path = Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("Ledger symlinks refused")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, (os.O_RDWR | os.O_CREAT if create else os.O_RDONLY) | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+" if create else "r", encoding="utf8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX if create else fcntl.LOCK_SH)
        stat = os.fstat(stream.fileno())
        if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
            raise PermissionError("Ledger must be owned by current operator and mode 0600")
        rows, previous = [], "0" * 64
        for line in stream:
            row = json.loads(line)
            body = {k: v for k, v in row.items() if k != "sha256"}
            if row.get("sequence") != len(rows) + 1 or row.get("previous") != previous or digest(body) != row.get("sha256"):
                raise ValueError("Ledger integrity failure")
            previous = row["sha256"]
            rows.append(row)
        yield stream, rows


def read_ledger(path):
    with locked_records(path) as (_, rows):
        return rows


def append_locked(stream, rows, payload):
    row = {"sequence": len(rows) + 1, "previous": rows[-1]["sha256"] if rows else "0" * 64,
           "recorded_at": utc_now(), "payload": payload}
    row["sha256"] = digest(row)
    stream.seek(0, os.SEEK_END)
    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    stream.flush()
    os.fsync(stream.fileno())
    rows.append(row)
    return row


def append_record(path, payload):
    with locked_records(path, create=True) as (stream, rows):
        return append_locked(stream, rows, payload)
