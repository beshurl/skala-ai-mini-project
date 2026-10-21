import os
from datetime import timedelta

import pytest

from recase import backup_receipts
from recase.backup_receipts import backup_inventory, create_backup, private_json, verify_backup
from recase.ledger import append_record, file_digest
from recase.lifecycle import inventory
from recase.retention_schedule import instant, plan_retention
from recase.store import Store

POLICY = {"scope": "personal_loopback_synthetic_service_only", "automatic_case_deletion": False,
          "automatic_backup_disposal": False, "case_retention_days": 90, "backup_retention_days": 30}


def source(tmp_path, pending=False):
    store = Store(tmp_path / "source.db")
    session = store.new_demo()
    case = store.cases(session["user_id"])[0]
    if pending:
        store.create_job(session["user_id"], case["id"], 1, {"backend": "synthetic-test-no-model"})
    journal = tmp_path / "current-journal.jsonl"
    append_record(journal, {"action": "initialize", "scope": "synthetic-test"})
    backup, receipt = tmp_path / "backup.db", tmp_path / "receipt.json"
    create_backup(store.path, backup, receipt)
    return store, session, case, journal, backup, receipt


def test_creation_receipt_and_actual_restore_check_keep_source_and_backup_unchanged(tmp_path):
    store, session, _, journal, backup, receipt = source(tmp_path, pending=True)
    before = {p: file_digest(p) for p in (store.path, journal, backup, receipt)}
    records = backup_inventory([receipt], [], journal, inventory(store.path))
    assert not records[0]["restore_verified"]
    verification = tmp_path / "verification.json"
    result = verify_backup(receipt, journal, tmp_path / "scratch", verification)
    assert all(result["checks"].values()) and result["jobs_marked_server_restarted"] == 1
    assert {p: file_digest(p) for p in before} == before
    assert store.session(session["token"]) and store.jobs(session["user_id"], store.cases(session["user_id"])[0]["id"])[0]["status"] == "QUEUED"
    records = backup_inventory([receipt], [verification], journal, inventory(store.path))
    assert records[0]["restore_verified"] and not records[0]["hold"]
    with Store(tmp_path / "scratch/restored.db", read_only=True).db() as db:
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM case_lifecycle WHERE hold=1").fetchone()[0] == 2


def test_backup_expiry_uses_recorded_creation_not_mtime_and_missing_verification_blocks(tmp_path):
    store, _, _, journal, backup, receipt = source(tmp_path)
    recorded = private_json(receipt)["created_at"]
    os.utime(backup, (0, 0))
    exported = inventory(store.path)
    exported["backups"] = backup_inventory([receipt], [], journal, exported)
    at = (instant(recorded) + timedelta(days=30)).isoformat()
    assert plan_retention(exported, POLICY, at)["eligible_for_review"] == 0
    verification = tmp_path / "verification.json"
    verify_backup(receipt, journal, tmp_path / "scratch", verification)
    exported["backups"] = backup_inventory([receipt], [verification], journal, exported)
    result = plan_retention(exported, POLICY, at)
    assert result["eligible_for_review"] == 1 and result["delete_actions_executed"] == 0
    assert exported["backups"][0]["created_at"] == recorded and backup.exists()


def test_later_journal_or_hold_makes_old_backup_ineligible(tmp_path):
    store, session, case, journal, _, receipt = source(tmp_path)
    verification = tmp_path / "verification.json"
    verify_backup(receipt, journal, tmp_path / "scratch", verification)
    store.transition_case(session["user_id"], case["id"], 1, 1, "hold", "Preserve copies containing this case")
    assert backup_inventory([receipt], [verification], journal, inventory(store.path))[0]["hold"]
    append_record(journal, {"action": "delete_case", "owner": session["user_id"], "case_id": case["id"]})
    assert not backup_inventory([receipt], [verification], journal, inventory(store.path))[0]["restore_verified"]


def test_changed_receipt_or_backup_bytes_fail_before_any_restore(tmp_path):
    _, _, _, journal, backup, receipt = source(tmp_path)
    original = receipt.read_bytes()
    receipt.write_text(receipt.read_text().replace("synthetic_fixture", "changed"))
    with pytest.raises(ValueError, match="integrity"):
        verify_backup(receipt, journal, tmp_path / "scratch", tmp_path / "verify.json")
    assert not (tmp_path / "scratch").exists()
    receipt.write_bytes(original)
    with backup.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="bytes changed"):
        verify_backup(receipt, journal, tmp_path / "scratch", tmp_path / "verify.json")
    assert not (tmp_path / "scratch").exists()


def test_schema1_backup_can_be_verified_but_is_never_reclassified_synthetic(tmp_path):
    store = Store(tmp_path / "old.db")
    store.new_demo()
    with store.db() as db:
        db.execute("DROP TABLE case_lifecycle_events")
        db.execute("DROP TABLE case_lifecycle")
        db.execute("PRAGMA user_version=1")
    journal = tmp_path / "journal.jsonl"
    append_record(journal, {"action": "initialize"})
    backup, receipt, verification = (tmp_path / name for name in ("backup.db", "receipt.json", "verification.json"))
    create_backup(store.path, backup, receipt)
    result = verify_backup(receipt, journal, tmp_path / "scratch", verification)
    assert result["scratch_schema_migration"]["status"] == "PASS"
    record = backup_inventory([receipt], [verification], journal, inventory(store.path))[0]
    assert record["restore_verified"] and record["data_class"] == "unclassified"
    assert plan_retention({"backups": [record]}, POLICY, "2030-01-01T00:00:00Z")["eligible_for_review"] == 0
    with Store(backup, read_only=True).db() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1


def test_current_journal_change_during_verify_never_produces_a_pass_receipt(tmp_path, monkeypatch):
    _, _, _, journal, backup, receipt = source(tmp_path)
    original = backup_receipts.apply_deletions
    def change_journal(*args, **kwargs):
        result = original(*args, **kwargs)
        append_record(journal, {"action": "initialize", "reason": "concurrent change fixture"})
        return result
    monkeypatch.setattr(backup_receipts, "apply_deletions", change_journal)
    with pytest.raises(RuntimeError, match="verification failed"):
        verify_backup(receipt, journal, tmp_path / "scratch", tmp_path / "verification.json")
    assert backup.exists() and (tmp_path / "scratch/restored.db").exists()
    assert not (tmp_path / "verification.json").exists()


def test_existing_destinations_duplicates_and_insecure_receipts_are_refused(tmp_path):
    store, _, _, journal, backup, receipt = source(tmp_path)
    before = file_digest(backup)
    with pytest.raises(FileExistsError):
        create_backup(store.path, backup, tmp_path / "new-receipt.json")
    assert not (tmp_path / "new-receipt.json").exists() and file_digest(backup) == before
    with pytest.raises(ValueError, match="Duplicate"):
        backup_inventory([receipt, receipt], [], journal, inventory(store.path))
    receipt.chmod(0o644)
    with pytest.raises(PermissionError):
        verify_backup(receipt, journal, tmp_path / "scratch", tmp_path / "verification.json")
    assert not (tmp_path / "scratch").exists()
