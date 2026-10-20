import fcntl
import sqlite3

import pytest

from recase.ledger import append_record
from recase.retention import apply_deletions, delete_case
from recase.store import NotFound, Store


def test_old_backup_does_not_revive_deleted_case_or_bearer_sessions(tmp_path):
    store = Store(tmp_path / "source.db")
    session = store.new_demo()
    case, other = store.cases(session["user_id"])
    job = store.create_job(session["user_id"], case["id"], 1, {"backend": "fixture"})
    backup = store.backup(tmp_path / "old-backup.db")
    ledger = tmp_path / "deletions.jsonl"
    result = delete_case(store.path, ledger, session["user_id"], case["id"])
    assert result["status"] == "PASS" and result["physical_erasure_verified"] is False
    with pytest.raises(NotFound):
        store.snapshot(session["user_id"], case["id"])
    restored = Store(backup)
    assert restored.snapshot(session["user_id"], case["id"])
    replay = apply_deletions(backup, ledger)
    assert replay["deleted_cases_replayed"] == 1
    for current in (store, restored):
        with pytest.raises(NotFound):
            current.job(session["user_id"], job["id"])
        with current.db() as db:
            assert db.execute("SELECT count(*) FROM events WHERE job_id=?", (job["id"],)).fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM evidence WHERE case_id=?", (case["id"],)).fetchone()[0] == 0
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert current.snapshot(session["user_id"], other["id"])
        with pytest.raises(NotFound):
            current.session(session["token"])
    assert apply_deletions(backup, ledger)["deleted_cases_replayed"] == 0


def test_deletion_rejects_wrong_owner_running_server_and_missing_journal(tmp_path):
    store = Store(tmp_path / "source.db")
    session = store.new_demo()
    case = store.cases(session["user_id"])[0]
    ledger = tmp_path / "deletions.jsonl"
    with pytest.raises(NotFound):
        delete_case(store.path, ledger, "wrong-owner", case["id"])
    assert not ledger.exists()
    lock_path = store.path.parent / (store.path.name + ".server.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="SERVER_RUNNING"):
            delete_case(store.path, ledger, session["user_id"], case["id"])
    with pytest.raises(FileNotFoundError):
        apply_deletions(store.path, ledger)
    append_record(ledger, {"action": "delete_case", "owner": session["user_id"], "case_id": case["id"]})
    # Covers crash after tombstone append but before source SQL deletion.
    assert apply_deletions(store.path, ledger)["deleted_cases_replayed"] == 1


def test_api_restart_replays_pending_deletion_before_any_service_read(tmp_path):
    from fastapi.testclient import TestClient
    from recase.api import create_app
    from recase.testing import FixtureModel
    store = Store(tmp_path / "source.db")
    session = store.new_demo()
    case = store.cases(session["user_id"])[0]
    ledger = tmp_path / "deletions.jsonl"
    append_record(ledger, {"action": "delete_case", "owner": session["user_id"], "case_id": case["id"]})
    with TestClient(create_app(store.path, FixtureModel(), testing=True, deletions_file=ledger)) as client:
        with store.db() as db:
            assert db.execute("SELECT count(*) FROM cases WHERE id=?", (case["id"],)).fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM evidence WHERE case_id=?", (case["id"],)).fetchone()[0] == 0
    with pytest.raises(RuntimeError, match="journal"):
        with TestClient(create_app(tmp_path / "missing.db", FixtureModel(), testing=True, deletions_file=tmp_path / "missing.jsonl")):
            pass
