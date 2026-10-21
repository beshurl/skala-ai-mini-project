from tests.account_helpers import enter_demo
import fcntl
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from recase import lifecycle
from recase.api import create_app
from recase.ledger import file_digest
from recase.retention import apply_deletions, delete_case
from recase.retention_schedule import plan_retention
from recase.store import Conflict, NotFound, Store
from recase.testing import FixtureModel

POLICY = {"scope": "personal_loopback_synthetic_service_only", "automatic_case_deletion": False,
          "automatic_backup_disposal": False, "case_retention_days": 90, "backup_retention_days": 30}


def demo(tmp_path):
    store = Store(tmp_path / "synthetic.db")
    session = store.new_demo()
    case = store.cases(session["user_id"])[0]
    return store, session["user_id"], case


def legacy(tmp_path):
    store, owner, case = demo(tmp_path)
    with store.db() as db:
        db.execute("DROP TABLE case_lifecycle_events")
        db.execute("DROP TABLE case_lifecycle")
        db.execute("PRAGMA user_version=1")
    return store, owner, case


def test_schema1_requires_explicit_backed_up_migration_and_keeps_unknown_history(tmp_path):
    store, owner, case = legacy(tmp_path)
    original = file_digest(store.path)
    before = store.snapshot(owner, case["id"])
    with pytest.raises(ValueError, match="MIGRATION_REQUIRED"):
        Store(store.path)
    assert file_digest(store.path) == original
    assert all(r["data_class"] == "unclassified" and r["closed_at"] is None for r in lifecycle.inventory(store.path)["cases"])
    backup = tmp_path / "rollback.db"
    report = lifecycle.migrate_v1(store.path, backup)
    assert report["status"] == "PASS" and report["historical_dates_inferred"] == 0
    assert Store(backup, read_only=True).snapshot(owner, case["id"]) == before
    migrated = Store(store.path)
    assert migrated.snapshot(owner, case["id"]) == before
    assert migrated.lifecycle(owner, case["id"])["created_at"] is None
    state = migrated.transition_case(owner, case["id"], 1, 1, "close", "Explicit close today; original creation is unknown")
    assert state["closed_at"] and state["data_class"] == "unclassified"
    assert plan_retention(lifecycle.inventory(store.path), POLICY, "2030-01-01T00:00:00Z")["eligible_for_review"] == 0
    assert lifecycle.migrate_v1(store.path, tmp_path / "unused.db")["status"] == "ALREADY_CURRENT"
    assert not (tmp_path / "unused.db").exists()


def test_migration_refuses_running_service_before_creating_backup(tmp_path):
    store, _, _ = legacy(tmp_path)
    original = file_digest(store.path)
    with (tmp_path / "synthetic.db.server.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="SERVER_RUNNING"):
            lifecycle.migrate_v1(store.path, tmp_path / "rollback.db")
    assert not (tmp_path / "rollback.db").exists() and file_digest(store.path) == original
    link = tmp_path / "link.db"
    link.symlink_to(store.path)
    with pytest.raises(PermissionError):
        lifecycle.migrate_v1(link, tmp_path / "rollback.db")


def test_failed_migration_rolls_back_schema_and_preserves_rollback_backup(tmp_path, monkeypatch):
    store, owner, case = legacy(tmp_path)
    monkeypatch.setattr(lifecycle, "TABLES", (lifecycle.TABLES[0], "INVALID SQL simulated migration fault"))
    backup = tmp_path / "rollback.db"
    with pytest.raises(sqlite3.OperationalError):
        lifecycle.migrate_v1(store.path, backup)
    with store.db() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='case_lifecycle_events'").fetchone()[0] == 0
    assert backup.is_file() and Store(backup, read_only=True).snapshot(owner, case["id"])


def test_malformed_schema1_is_refused_before_a_backup_or_migration(tmp_path):
    store, _, _ = legacy(tmp_path)
    with store.db() as db:
        db.execute("ALTER TABLE cases ADD COLUMN unexpected TEXT")
    original = file_digest(store.path)
    with pytest.raises(ValueError, match="column contract"):
        lifecycle.migrate_v1(store.path, tmp_path / "rollback.db")
    assert file_digest(store.path) == original and not (tmp_path / "rollback.db").exists()


def test_explicit_close_reopen_hold_and_idempotent_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle.time, "time", lambda: 1000)
    store, owner, case = demo(tmp_path)
    state = store.lifecycle(owner, case["id"])
    assert state["created_at"] == "1970-01-01T00:16:40+00:00" and state["closed_at"] is None
    monkeypatch.setattr(lifecycle.time, "time", lambda: 900)
    with pytest.raises(Conflict, match="CLOCK_BEFORE"):
        store.transition_case(owner, case["id"], 1, 1, "close", "Clock moved backwards")
    monkeypatch.setattr(lifecycle.time, "time", lambda: 2000)
    closed = store.transition_case(owner, case["id"], 1, 1, "close", "Operator closed synthetic test case")
    monkeypatch.setattr(lifecycle.time, "time", lambda: 3000)
    assert store.transition_case(owner, case["id"], 1, 2, "close", "Retry close") == closed
    assert plan_retention(lifecycle.inventory(store.path), POLICY, "2026-10-20T00:00:00Z")["eligible_for_review"] == 1
    held = store.transition_case(owner, case["id"], 1, 2, "hold", "Preserve for review")
    assert held["hold"] and held["closed_at"] == closed["closed_at"]
    assert plan_retention(lifecycle.inventory(store.path), POLICY, "2026-10-20T00:00:00Z")["eligible_for_review"] == 0
    opened = store.transition_case(owner, case["id"], 1, 3, "reopen", "Continue work")
    assert opened["closed_at"] is None and opened["hold"]
    released = store.transition_case(owner, case["id"], 1, 4, "release_hold", "Review finished")
    assert not released["hold"]
    assert plan_retention(lifecycle.inventory(store.path), POLICY, "2026-10-20T00:00:00Z")["eligible_for_review"] == 0
    reclosed = store.transition_case(owner, case["id"], 1, 5, "close", "Closed after new work")
    assert reclosed["closed_at"] != closed["closed_at"]


def test_active_job_stale_versions_and_closed_case_mutations_are_blocked(tmp_path):
    store, owner, case = demo(tmp_path)
    with pytest.raises(NotFound):
        store.transition_case("wrong-owner", case["id"], 1, 1, "close", "Other case")
    for version, revision in ((2, 1), (1, 2)):
        with pytest.raises(Conflict):
            store.transition_case(owner, case["id"], version, revision, "close", "Stale request")
    job = store.create_job(owner, case["id"], 1, {"backend": "fixture"})
    with pytest.raises(Conflict, match="ACTIVE_JOB"):
        store.transition_case(owner, case["id"], 1, 1, "close", "Job still active")
    store.set_status(owner, job["id"], "FAILED", error="fixture-only")
    store.transition_case(owner, case["id"], 1, 1, "close", "Job terminal")
    with pytest.raises(Conflict, match="CASE_CLOSED"):
        store.create_job(owner, case["id"], 1, {})
    with pytest.raises(Conflict, match="CASE_CLOSED"):
        store.release_next(owner, case["id"], 1)
    assert store.snapshot(owner, case["id"])["evidence_version"] == 1


def test_delete_replays_lifecycle_purge_and_restore_automatically_holds_survivors(tmp_path):
    store, owner, case = demo(tmp_path)
    other = store.cases(owner)[1]
    store.transition_case(owner, other["id"], 1, 1, "close", "Closed before backup")
    backup = store.backup(tmp_path / "old-backup.db")
    ledger = tmp_path / "deletions.jsonl"
    delete_case(store.path, ledger, owner, case["id"])
    replay = apply_deletions(backup, ledger)
    assert replay["retention_holds_applied"] == 1
    for current in (store.path, backup):
        with Store(current, read_only=True).db() as db:
            for table in ("case_lifecycle", "case_lifecycle_events"):
                assert db.execute(f"SELECT count(*) FROM {table} WHERE case_id=?", (case["id"],)).fetchone()[0] == 0
    restored = Store(backup)
    assert restored.lifecycle(owner, other["id"])["hold"]
    revision = restored.lifecycle(owner, other["id"])["revision"]
    assert apply_deletions(backup, ledger)["retention_holds_applied"] == 0
    assert restored.lifecycle(owner, other["id"])["revision"] == revision
    assert plan_retention(lifecycle.inventory(backup), POLICY, "2030-01-01T00:00:00Z")["eligible_for_review"] == 0


def test_inventory_is_read_only_metadata_and_contains_no_case_text_or_owner(tmp_path):
    store, owner, case = demo(tmp_path)
    before = file_digest(store.path)
    exported = lifecycle.inventory(store.path)
    encoded = json.dumps(exported)
    assert owner not in encoded and case["id"] not in encoded and case["title"] not in encoded
    assert "claims" not in encoded and "sessions" not in encoded and file_digest(store.path) == before


def test_lifecycle_read_exposes_current_evidence_version_for_stale_view_detection(tmp_path):
    store, owner, case = demo(tmp_path)
    assert store.lifecycle(owner, case["id"])["evidence_version"] == 1
    store.release_next(owner, case["id"], 1)
    current = store.lifecycle(owner, case["id"])
    assert current["evidence_version"] == 2 and current["revision"] == 1
    with pytest.raises(Conflict, match="EVIDENCE_VERSION_CHANGED"):
        store.transition_case(owner, case["id"], 1, current["revision"], "close", "Outdated case content")


def test_lifecycle_api_enforces_owner_csrf_versions_and_closed_mutations(tmp_path):
    with TestClient(create_app(tmp_path / "api.db", FixtureModel(), testing=True)) as client:
        assert client.get("/api/cases/no-case/lifecycle").status_code == 401
        session = enter_demo(client).json()
        case = client.get("/api/cases").json()[0]
        endpoint = f'/api/cases/{case["id"]}/lifecycle'
        body = {"evidence_version": 1, "lifecycle_revision": 1, "action": "close", "reason": "Case review finished"}
        assert client.post(endpoint, json=body).status_code == 403
        client.headers["x-recase-csrf"] = session["csrf"]
        assert client.post(endpoint, json={**body, "reason": " "}).status_code == 422
        assert client.post(endpoint, json={**body, "lifecycle_revision": True}).status_code == 422
        assert client.post(endpoint, json=body).json()["closed_at"]
        assert client.post(endpoint, json=body).status_code == 409
        assert client.post(f'/api/cases/{case["id"]}/analyses', json={"evidence_version": 1}).status_code == 409
        assert client.post(f'/api/cases/{case["id"]}/release', json={"evidence_version": 1}).status_code == 409
        client.cookies.clear()
        other = enter_demo(client).json()
        client.headers["x-recase-csrf"] = other["csrf"]
        assert client.get(endpoint).status_code == 404
        assert client.post(endpoint, json=body).status_code == 404
