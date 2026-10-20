"""Single-operator loopback HTTP Basic access key, not remote/multiuser auth."""
import base64
import hashlib
import json
import os
import secrets
import stat
import time
from pathlib import Path


def key_digest(user, token):
    return hashlib.sha256((user + "\0" + token).encode()).hexdigest()


def protected_file(path):
    path = Path(path).absolute()
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise PermissionError("Regular auth file required; symlinks refused")
    if path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077:
        raise PermissionError("Auth file requires current UID ownership and mode0600")
    return path


class LocalAuth:
    def __init__(self, path):
        self.path = protected_file(path)
        self.initial = self.path.read_bytes()
        config = json.loads(self.initial)
        self.user, self.digest = config["user"], config["key_sha256"]
        self.sessions = {}
        if config.get("scheme") != "random256-local-basic-v1" or not self.user or len(self.digest) != 64:
            raise ValueError("Unsupported local credential config")

    def unchanged(self):
        try:
            return protected_file(self.path).read_bytes() == self.initial
        except OSError:
            return False

    def permits(self, authorization="", session_cookie=""):
        # Rotation/revocation on disk fails closed until the process restarts.
        try:
            if not self.unchanged():
                return False
            session_hash = hashlib.sha256(session_cookie.encode()).hexdigest()
            if session_cookie and self.sessions.get(session_hash, 0) > time.monotonic():
                return True
            scheme, encoded = authorization.split(" ", 1)
            if scheme.casefold() != "basic" or len(encoded) > 512:
                return False
            user, token = base64.b64decode(encoded, validate=True).decode("utf8").split(":", 1)
            if not user.isascii() or not token.isascii():
                return False
            return secrets.compare_digest(user, self.user) and secrets.compare_digest(key_digest(user, token), self.digest)
        except (OSError, ValueError, KeyError, UnicodeError):
            return False

    def new_session(self):
        self.sessions = {key: expiry for key, expiry in self.sessions.items() if expiry > time.monotonic()}
        if len(self.sessions) >= 16:
            self.sessions.pop(next(iter(self.sessions)))
        token = secrets.token_urlsafe(32)
        self.sessions[hashlib.sha256(token.encode()).hexdigest()] = time.monotonic() + 3600
        return token


def provision(directory, user):
    if not user or ":" in user or not user.isascii() or len(user) > 64:
        raise ValueError("ASCII local username without colon required")
    path = Path(directory).absolute()
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    token = secrets.token_urlsafe(32)
    for name, text in (("key.txt", token + "\n"), ("auth.json", json.dumps({"scheme": "random256-local-basic-v1",
                                                                            "user": user, "key_sha256": key_digest(user, token)}, indent=2))):
        fd = os.open(path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
    return {"user": user, "config": str(path / "auth.json"), "key_file": str(path / "key.txt"), "secret_printed": False}
