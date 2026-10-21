"""Temporary synthetic sources only; no privileged command or live DB mutation."""
import json
import os
import stat
from pathlib import Path

import pytest

from recase.ledger import append_record, digest, file_digest
from recase.operations_drill import run
from recase import operations_drill
from recase.paths import BACKEND_ROOT
from recase.store import Store
from scripts import verify_isolated_operations as helper


def fixture_source(tmp_path):
    db = Store(tmp_path / "synthetic-source.db")
    session = db.new_demo()
    case = db.cases(session["user_id"])[0]
    db.create_job(session["user_id"], case["id"], 1, {"backend": "UNIT_TEST_NO_MODEL"})
    journal = tmp_path / "journal.jsonl"
    append_record(journal, {"action": "initialize", "scope": "UNIT_TEST_ONLY"})
    return db, journal


def test_read_only_backup_and_copy_only_deletion_restore_preserve_source_and_journal(tmp_path):
    db, journal = fixture_source(tmp_path)
    before_db, before_journal = file_digest(db.path), journal.read_bytes()
    out = tmp_path / "private-drill"
    result = run(BACKEND_ROOT, db.path, journal, out, os.getuid())
    assert result["status"] == "PASS" and all(result["checks"].values())
    assert result["worker_uid"] == os.getuid() != 0
    assert result["production_delete_calls"] == result["model_calls"] == result["training_runs"] == 0
    assert result["backup_bytes_erased"] is False and result["physical_erasure_verified"] is False
    assert file_digest(db.path) == before_db and journal.read_bytes() == before_journal
    with db.db() as conn:
        assert conn.execute("SELECT count(*) FROM cases").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
        assert conn.execute("SELECT status FROM jobs").fetchone()[0] == "QUEUED"
        assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
    with Store(out / "restored.db", read_only=True).db() as conn:
        assert conn.execute("SELECT count(*) FROM cases").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert conn.execute("SELECT status,error FROM jobs").fetchone()[:] == ("FAILED", "SERVER_RESTARTED")
    assert result["restored_jobs_marked_server_restarted"] == 1
    assert stat.S_IMODE(out.stat().st_mode) == 0o700
    assert stat.S_IMODE((out / "live-backup.db").stat().st_mode) == 0o600
    with pytest.raises(FileExistsError, match="new private"):
        run(BACKEND_ROOT, db.path, journal, out, os.getuid())
    assert file_digest(db.path) == before_db and journal.read_bytes() == before_journal


def test_wrong_uid_or_root_is_refused_before_file_access(tmp_path):
    for uid in (0, os.getuid() + 1):
        with pytest.raises(PermissionError, match="nonroot"):
            run(BACKEND_ROOT, tmp_path / "no-db", tmp_path / "no-journal", tmp_path / "out", uid)
    assert not (tmp_path / "out").exists()


def test_schema1_source_is_migrated_only_in_the_new_drill_copy(tmp_path):
    db, journal = fixture_source(tmp_path)
    with db.db() as conn:
        conn.execute("DROP TABLE case_lifecycle_events")
        conn.execute("DROP TABLE case_lifecycle")
        conn.execute("PRAGMA user_version=1")
    original = file_digest(db.path)
    result = run(BACKEND_ROOT, db.path, journal, tmp_path / "drill", os.getuid())
    assert result["status"] == "PASS" and result["source_schema"] == 1
    assert result["scratch_schema_migration"]["status"] == "PASS"
    assert file_digest(db.path) == original
    with db.db() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_missing_insecure_or_symlinked_journal_cannot_start_a_backup(tmp_path):
    db, journal = fixture_source(tmp_path)
    with pytest.raises(FileNotFoundError):
        run(BACKEND_ROOT, db.path, tmp_path / "absent", tmp_path / "out", os.getuid())
    journal.chmod(0o644)
    with pytest.raises(PermissionError, match="mode0600"):
        run(BACKEND_ROOT, db.path, journal, tmp_path / "out", os.getuid())
    journal.chmod(0o600)
    link = tmp_path / "linked-journal"
    link.symlink_to(journal)
    with pytest.raises(PermissionError, match="regular"):
        run(BACKEND_ROOT, db.path, link, tmp_path / "out", os.getuid())
    assert not (tmp_path / "out").exists()


def test_corrupt_independent_journal_is_rejected_before_backup(tmp_path):
    db, journal = fixture_source(tmp_path)
    journal.write_text(journal.read_text().replace("UNIT_TEST_ONLY", "CHANGED"))
    with pytest.raises(ValueError, match="integrity"):
        run(BACKEND_ROOT, db.path, journal, tmp_path / "out", os.getuid())
    assert not (tmp_path / "out").exists()


def test_low_disk_space_refuses_before_creating_copies(tmp_path, monkeypatch):
    db, journal = fixture_source(tmp_path)
    from collections import namedtuple
    Usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(operations_drill.shutil, "disk_usage", lambda _: Usage(100, 100, 0))
    with pytest.raises(RuntimeError, match="free disk"):
        run(BACKEND_ROOT, db.path, journal, tmp_path / "out", os.getuid())
    assert not (tmp_path / "out").exists()


def test_apply_requires_root_before_reading_a_plan(monkeypatch):
    monkeypatch.setattr(helper.os, "geteuid", lambda: 501)
    with pytest.raises(PermissionError, match="sudo"):
        helper.apply("ABSENT_UNIT_TEST_PLAN")


def test_plan_file_tampering_and_exposed_permissions_are_refused(tmp_path):
    path = tmp_path / "plan.json"
    value = {"version": "isolated-operations-v1", "operator_uid": os.getuid(), "scope": "UNIT_TEST_ONLY"}
    value["plan_sha256"] = digest(value)
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    assert helper.checked_plan(path) == value
    path.write_text(path.read_text().replace("UNIT_TEST_ONLY", "TAMPERED"))
    with pytest.raises(ValueError, match="changed"):
        helper.checked_plan(path)
    path.chmod(0o644)
    with pytest.raises(PermissionError, match="Private"):
        helper.checked_plan(path)


def test_changed_deployed_source_is_refused(tmp_path, monkeypatch):
    deploy = tmp_path / "deployment"
    directory = deploy / "app/backend/recase"
    directory.mkdir(parents=True)
    for name in helper.MODULES:
        (directory / name).write_bytes((BACKEND_ROOT / "recase" / name).read_bytes())
        (directory / name).chmod(0o644)
    monkeypatch.setattr(helper, "root_path", lambda *a, **k: None)  # Explicit temporary fixture, not root evidence.
    assert len(helper.public_sources(deploy)) == len(helper.MODULES)
    (directory / "retention.py").write_text("# CHANGED UNIT_TEST_SOURCE\n")
    with pytest.raises(ValueError, match="differ"):
        helper.public_sources(deploy)
