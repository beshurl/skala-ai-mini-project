"""Disposable SQLite probes only. No root or live-service access in tests."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import diagnose_local_service as diagnostic


def probe(path):
    result = subprocess.run([sys.executable, "-I", "-c", diagnostic.PROBE, str(path)],
                            capture_output=True, text=True, timeout=10, check=True)
    return json.loads(result.stdout)


def test_missing_database_is_never_created(tmp_path):
    path = tmp_path / "missing.db"
    result = probe(path)
    assert not path.exists()
    assert result["classification"] == "DATABASE_MISSING_OR_UNSAFE"
    assert result["job_state"] == "UNKNOWN" and not result["database_opened"]


def test_live_wal_jobs_are_visible_without_raw_text_or_ids(tmp_path):
    path = tmp_path / "fixture.db"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE jobs(id TEXT,status TEXT,cancel_requested INTEGER,created REAL,private_text TEXT)")
        db.execute("INSERT INTO jobs VALUES('PRIVATE_JOB_ID','RUNNING',1,0,'PRIVATE_CASE_OR_SECRET')")
        db.commit()
        result = probe(path)
        assert result["active_jobs"] == 1 and result["job_state"] == "ACTIVE"
        assert result["active_samples"][0]["cancel_requested"] is True
        assert "PRIVATE_" not in json.dumps(result)
        assert db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1


def test_sqlite_error_codes_are_reported_without_database_content(tmp_path):
    path = tmp_path / "fixture.db"
    path.write_bytes(b"PRIVATE_NOT_A_DATABASE")
    result = probe(path)
    assert result["classification"] == "READ_ONLY_QUERY_FAILED"
    assert result["error"]["sqlite_errorcode"] == sqlite3.SQLITE_NOTADB
    assert "PRIVATE_NOT_A_DATABASE" not in json.dumps(result)
    assert result["job_state"] == "UNKNOWN"


def test_symlink_database_is_not_followed(tmp_path):
    path = tmp_path / "fixture.db"
    path.symlink_to(tmp_path / "target.db")
    result = probe(path)
    assert result["classification"] == "DATABASE_MISSING_OR_UNSAFE"
    assert not (tmp_path / "target.db").exists()


def test_without_admin_no_service_or_subprocess_is_touched(monkeypatch):
    monkeypatch.setattr(diagnostic.os, "geteuid", lambda: 501)
    def forbidden(*args, **kwargs):
        pytest.fail("No privileged access or subprocess without administrator")
    monkeypatch.setattr(diagnostic, "validate_identity", forbidden)
    monkeypatch.setattr(diagnostic.subprocess, "run", forbidden)
    result = diagnostic.inspect_service(41133)
    assert result["status"] == "ADMIN_AUTH_REQUIRED" and result["probe_executed"] is False


def test_changed_service_identity_stops_before_database_probe(monkeypatch):
    monkeypatch.setattr(diagnostic.os, "geteuid", lambda: 0)
    def changed(*args):
        raise ValueError("RUNNING_DAEMON_PID_CHANGED")
    monkeypatch.setattr(diagnostic, "validate_identity", changed)
    def forbidden(*args, **kwargs):
        pytest.fail("Do not probe a different service")
    monkeypatch.setattr(diagnostic.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="PID_CHANGED"):
        diagnostic.inspect_service(41133)
