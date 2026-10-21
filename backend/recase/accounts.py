"""Local email/password accounts and revocable, memory-only browser sessions."""
import hashlib
import os
import re
import secrets
import sqlite3
import stat
import threading
import time
import uuid
from collections import OrderedDict, deque
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from recase.account_state import account_lock

COOKIE = "recase_account"
SESSION_SECONDS = 3600
SCRYPT = {"n": 32768, "r": 8, "p": 3, "dklen": 32, "maxmem": 64 * 1024 * 1024}


def normalize_email(value):
    email = value.strip().casefold()
    if len(email) > 254 or not email.isascii() or not re.fullmatch(r"[^\s@\x00-\x1f]+@[^\s@.]+(?:\.[^\s@.]+)+", email):
        raise HTTPException(422, detail="INVALID_EMAIL")
    return email


def check_password(value):
    if not 12 <= len(value) <= 128 or "\x00" in value or not value.strip():
        raise HTTPException(422, detail="PASSWORD_LENGTH")
    try:
        value.encode("utf8")
    except UnicodeError:
        raise HTTPException(422, detail="AUTH_INPUT_INVALID") from None


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    result = hashlib.scrypt(password.encode("utf8"), salt=salt, **SCRYPT)
    return "scrypt$32768$8$3$" + salt.hex() + "$" + result.hex()


def password_matches(password, encoded):
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if (scheme, n, r, p) != ("scrypt", "32768", "8", "3") or len(salt) != 32 or len(expected) != 64:
            return False
        actual = password_hash(password, bytes.fromhex(salt)).rsplit("$", 1)[1]
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


class Accounts:
    def __init__(self, path):
        self.path = Path(path).absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.parent.stat().st_uid != os.geteuid() or self.path.parent.stat().st_mode & 0o022:
            raise PermissionError("Account directory must be operator owned and not writable by other users")
        if not self.path.exists():
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        self._check_file()
        info = self.path.stat()
        self._file_identity = (info.st_dev, info.st_ino)
        self._initializing = True
        with self.db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1) or version == 0 and db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
                raise ValueError("Unrecognized account database; automatic migration refused")
            if version == 1:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                columns = [row[1] for row in db.execute("PRAGMA table_info(accounts)")]
                if tables != {"accounts"} or columns != ["id", "email", "name", "password_hash", "role", "enabled", "credential_version", "created"]:
                    raise ValueError("Account schema differs from the recognized version")
            db.execute("CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','admin')),enabled INTEGER NOT NULL DEFAULT 1,credential_version INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL)")
            db.execute("PRAGMA user_version=1")
        self._initializing = False
        self._lock = threading.RLock()
        self._hash_slots = threading.BoundedSemaphore(2)
        self._sessions, self._attempts = OrderedDict(), OrderedDict()
        self._dummy = password_hash(secrets.token_urlsafe(32))

    def _check_file(self):
        info = self.path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077
                or info.st_nlink != 1 or any(p.is_symlink() for p in self.path.parents)):
            raise PermissionError("Account database must be operator-owned, regular and mode0600")
        if hasattr(self, "_file_identity") and self._file_identity != (info.st_dev, info.st_ino):
            raise RuntimeError("ACCOUNT_DATABASE_REPLACED_RESTART_REQUIRED")

    @contextmanager
    def db(self):
        with account_lock(self.path):
            with self._connection() as connection:
                yield connection

    @contextmanager
    def _connection(self):
        self._check_file()
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        try:
            if not self._initializing and connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Account schema no longer usable; restart after reviewed recovery")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def hash_slot(self):
        if not self._hash_slots.acquire(blocking=False):
            raise HTTPException(429, detail="LOGIN_RATE_LIMITED", headers={"Retry-After": "60"})
        try:
            yield
        finally:
            self._hash_slots.release()

    def throttle(self, operation, ip, email=""):
        now = time.monotonic()
        keys = [(operation + ":ip:" + ip, 20), (operation + ":account:" + hashlib.sha256(email.encode()).hexdigest(), 8)]
        with self._lock:
            for key, limit in keys:
                attempts = self._attempts.setdefault(key, deque())
                while attempts and attempts[0] <= now - 60:
                    attempts.popleft()
                if len(attempts) >= limit:
                    raise HTTPException(429, detail="LOGIN_RATE_LIMITED", headers={"Retry-After": "60"})
            for key, _ in keys:
                self._attempts[key].append(now)
                self._attempts.move_to_end(key)
            while len(self._attempts) > 1024:
                self._attempts.popitem(last=False)

    def create(self, email, password, name, *, role="user"):
        email = normalize_email(email)
        check_password(password)
        name = name.strip()
        if not 1 <= len(name) <= 40 or any(ord(c) < 32 for c in name) or role not in {"user", "admin"}:
            raise HTTPException(422, detail="AUTH_INPUT_INVALID")
        with self.hash_slot():
            encoded = password_hash(password)
        user_id = "USER-" + uuid.uuid4().hex
        try:
            with self.db() as db:
                db.execute("INSERT INTO accounts(id,email,name,password_hash,role,created) VALUES(?,?,?,?,?,?)",
                           (user_id, email, name, encoded, role, time.time()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, detail="EMAIL_IN_USE") from None
        return self.get(user_id)

    def get(self, user_id):
        with self.db() as db:
            row = db.execute("SELECT id,email,name,role,enabled,credential_version FROM accounts WHERE id=?", (user_id,)).fetchone()
        if not row or not row["enabled"]:
            raise HTTPException(401, detail="AUTH_REQUIRED")
        return dict(row)

    def login(self, email, password, ip):
        email = normalize_email(email)
        self.throttle("login", ip, email)
        with self.db() as db:
            row = db.execute("SELECT id,password_hash,enabled FROM accounts WHERE email=?", (email,)).fetchone()
        with self.hash_slot():
            valid = password_matches(password, row["password_hash"] if row else self._dummy)
        if not row or not row["enabled"] or not valid:
            raise HTTPException(401, detail="LOGIN_FAILED")
        return self.new_session(self.get(row["id"]))

    def new_session(self, user):
        cookie, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.monotonic()
        with self._lock:
            self._sessions = OrderedDict((k, v) for k, v in self._sessions.items() if v["expires"] > now)
            own = [k for k, v in self._sessions.items() if v["user_id"] == user["id"]]
            for key in own[:-4]:
                self._sessions.pop(key)
            while len(self._sessions) >= 512:
                self._sessions.popitem(last=False)
            self._sessions[hashlib.sha256(cookie.encode()).hexdigest()] = {
                "user_id": user["id"], "csrf": csrf, "expires": now + SESSION_SECONDS,
                "credential_version": user["credential_version"], "role": user["role"]}
        return cookie, {"user_id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"], "csrf": csrf}

    def session(self, cookie):
        key = hashlib.sha256(cookie.encode()).hexdigest()
        with self._lock:
            record = self._sessions.get(key)
            if not record or record["expires"] <= time.monotonic():
                self._sessions.pop(key, None)
                raise HTTPException(401, detail="AUTH_REQUIRED")
            record = dict(record)
        user = self.get(record["user_id"])
        if user["credential_version"] != record["credential_version"] or user["role"] != record["role"]:
            self.revoke(cookie)
            raise HTTPException(401, detail="AUTH_REQUIRED")
        return {"user_id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"], "csrf": record["csrf"]}

    def require(self, request, write=False, admin=False):
        try:
            value = self.session(request.cookies.get(COOKIE, ""))
        except (OSError, sqlite3.DatabaseError, RuntimeError, ValueError):
            raise HTTPException(503, detail="ACCOUNT_STORE_UNAVAILABLE") from None
        if admin and value["role"] != "admin":
            raise HTTPException(403, detail="ADMIN_REQUIRED")
        if write and not secrets.compare_digest(request.headers.get("x-recase-csrf", ""), value["csrf"]):
            raise HTTPException(403, detail="CSRF_REQUIRED")
        return value

    def revoke(self, cookie):
        with self._lock:
            self._sessions.pop(hashlib.sha256(cookie.encode()).hexdigest(), None)

    def reset_password(self, email, password):
        check_password(password)
        with self.hash_slot():
            encoded = password_hash(password)
        with self.db() as db:
            result = db.execute("UPDATE accounts SET password_hash=?,credential_version=credential_version+1 WHERE email=?",
                                (encoded, normalize_email(email)))
            if not result.rowcount:
                raise ValueError("Account not found")

    def close(self):
        with self._lock:
            self._sessions.clear()
