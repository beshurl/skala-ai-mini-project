import json
import os
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from recase import encrypted_backups as encrypted
from recase.ledger import append_record, digest, file_digest
from recase.lifecycle import inventory
from recase.retention_schedule import plan_retention
from recase.store import Store

POLICY = {"scope": "personal_loopback_synthetic_service_only", "automatic_case_deletion": False,
          "automatic_backup_disposal": False, "case_retention_days": 90, "backup_retention_days": 30}


def setup(tmp_path):
    store = Store(tmp_path / "source.db")
    session = store.new_demo()
    cases = store.cases(session["user_id"])
    for name in ("backups", "keys"):
        (tmp_path / name).mkdir(mode=0o700)
    journal = tmp_path / "deletions.jsonl"
    append_record(journal, {"action": "initialize", "policy": "synthetic-encryption-test-only"})
    return store, session, cases, journal


def backup(tmp_path, store, name="first"):
    archive, key, receipt = (tmp_path / "backups" / f"{name}.recase", tmp_path / "keys" / f"{name}.key",
                             tmp_path / "backups" / f"{name}.json")
    result = encrypted.create_encrypted_backup(store.path, archive, key, receipt)
    assert result["status"] == "PASS" and result["plaintext_backup_files_created"] == 0
    return archive, key, receipt


def verify(tmp_path, receipt, key, journal, name="verified"):
    scratch, report = tmp_path / name, tmp_path / f"{name}.json"
    result = encrypted.verify_encrypted_backup(receipt, key, journal, scratch, report)
    assert result["status"] == "PASS" and result["physical_or_crypto_erasure_verified"] is False
    return scratch, report, result


def test_new_independent_keys_no_plain_backup_and_committed_wal_restore(tmp_path):
    store, session, cases, journal = setup(tmp_path)
    # Keep a writer open so committed evidence still has a WAL file at snapshot.
    with store.db() as writer:
        writer.execute("UPDATE cases SET summary='Synthetic WAL-only marker' WHERE id=?", (cases[0]["id"],))
        writer.commit()
        assert Path(str(store.path) + "-wal").stat().st_size > 0
        first = backup(tmp_path, store)
        second = backup(tmp_path, store, "second")
    assert first[1].read_bytes() != second[1].read_bytes()
    one, _, _, _ = encrypted.read_receipt(first[2])
    two, _, _, _ = encrypted.read_receipt(second[2])
    assert one["header"]["nonce_hex"] != two["header"]["nonce_hex"]
    assert set(p.suffix for p in (tmp_path / "backups").iterdir()) == {".recase", ".json"}
    assert first[0].read_bytes().startswith(encrypted.MAGIC)
    assert b"Synthetic WAL-only marker" not in first[0].read_bytes()
    scratch, _, _ = verify(tmp_path, first[2], first[1], journal)
    restored = Store(scratch / "restored.db", read_only=True)
    assert restored.snapshot(session["user_id"], cases[0]["id"])["summary"] == "Synthetic WAL-only marker"
    for path in (*first, *second):
        assert path.stat().st_mode & 0o777 == 0o600
    assert not any("key" in k for k in json.loads(first[2].read_text()))


def test_restore_replays_current_tombstone_revokes_sessions_clears_jobs_and_holds_survivor(tmp_path):
    store, session, cases, journal = setup(tmp_path)
    pending = store.create_job(session["user_id"], cases[1]["id"], 1, {"backend": "synthetic_no_model"})
    archive, key, receipt = backup(tmp_path, store)
    append_record(journal, {"action": "delete_case", "owner": session["user_id"], "case_id": cases[0]["id"]})
    before = {p: file_digest(p) for p in (store.path, archive, key, receipt, journal)}
    scratch, _, result = verify(tmp_path, receipt, key, journal)
    assert result["replay"]["deleted_cases_replayed"] == 1 and result["jobs_marked_server_restarted"] == 1
    restored = Store(scratch / "restored.db", read_only=True)
    with restored.db() as db:
        assert db.execute("SELECT count(*) FROM cases WHERE id=?", (cases[0]["id"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert restored.job(session["user_id"], pending["id"])["status"] == "FAILED"
    assert restored.lifecycle(session["user_id"], cases[1]["id"])["hold"]
    assert all(file_digest(p) == value for p, value in before.items())
    assert store.snapshot(session["user_id"], cases[0]["id"])


def test_wrong_missing_and_changed_key_never_create_a_plaintext_destination(tmp_path):
    store, _, _, journal = setup(tmp_path)
    _, key, receipt = backup(tmp_path, store)
    wrong = tmp_path / "keys" / "wrong.key"
    wrong.write_bytes(os.urandom(32)); wrong.chmod(0o600)
    with pytest.raises(InvalidTag):
        encrypted.verify_encrypted_backup(receipt, wrong, journal, tmp_path / "wrong", tmp_path / "wrong.json")
    assert not (tmp_path / "wrong").exists() and not (tmp_path / "wrong.json").exists()
    moved = key.with_suffix(".offline")
    key.rename(moved)
    try:
        with pytest.raises(FileNotFoundError):
            encrypted.verify_encrypted_backup(receipt, key, journal, tmp_path / "missing", tmp_path / "missing.json")
        assert not (tmp_path / "missing").exists()
    finally:
        moved.rename(key)  # Reversible unavailability rehearsal; no key erasure.
    verify(tmp_path, receipt, key, journal)


@pytest.mark.parametrize("tamper", ["ciphertext", "header"])
def test_aead_rejects_tampering_even_after_unkeyed_receipt_hashes_are_recomputed(tmp_path, tamper):
    store, _, _, journal = setup(tmp_path)
    archive, key, receipt = backup(tmp_path, store)
    obj = json.loads(receipt.read_text())
    body = archive.read_bytes()
    if tamper == "ciphertext":
        body = body[:-1] + bytes([body[-1] ^ 1])
    else:
        _, aad, ciphertext, _ = encrypted.read_receipt(receipt)
        obj["header"]["initial_hold"] = not obj["header"]["initial_hold"]
        changed = encrypted.canonical(obj["header"])
        body = encrypted.MAGIC + len(changed).to_bytes(4, "big") + changed + ciphertext
    archive.write_bytes(body)
    obj["encrypted_sha256"] = encrypted.sha_bytes(body)
    obj["receipt_sha256"] = digest({k: v for k, v in obj.items() if k != "receipt_sha256"})
    receipt.write_text(json.dumps(obj))
    with pytest.raises(InvalidTag):
        encrypted.verify_encrypted_backup(receipt, key, journal, tmp_path / "tampered", tmp_path / "tampered.json")
    assert not (tmp_path / "tampered").exists() and not (tmp_path / "tampered.json").exists()


def test_legacy_snapshot_is_only_migrated_in_new_scratch_and_remains_unclassified(tmp_path):
    store, _, _, journal = setup(tmp_path)
    with store.db() as db:
        db.execute("DROP TABLE case_lifecycle_events")
        db.execute("DROP TABLE case_lifecycle")
        db.execute("PRAGMA user_version=1")
    before = file_digest(store.path)
    _, key, receipt = backup(tmp_path, store)
    scratch, _, result = verify(tmp_path, receipt, key, journal)
    assert result["scratch_schema_migration"]["status"] == "PASS" and file_digest(store.path) == before
    legacy = Store(store.path, read_only=True)
    with legacy.db() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert all(c["data_class"] == "unclassified" and c["created_at"] is None and c["closed_at"] is None and c["hold"] for c in inventory(scratch / "restored.db")["cases"])


def test_inventory_requires_available_verified_key_current_journal_and_respects_later_hold(tmp_path):
    store, session, cases, journal = setup(tmp_path)
    _, key, receipt = backup(tmp_path, store)
    _, proof, _ = verify(tmp_path, receipt, key, journal)
    export = lambda keys: encrypted.encrypted_inventory([receipt], [proof], keys, journal, inventory(store.path))
    report = {**inventory(store.path), "backups": export([key])}
    assert report["backups"][0]["restore_verified"]
    plan = plan_retention(report, POLICY, "2035-01-01T00:00:00Z")
    assert next(r for r in plan["rows"] if r["kind"] == "backup")["eligible"]
    missing = key.with_name("missing.key")
    assert not export([missing])[0]["restore_verified"]
    colocated = tmp_path / "backups/key-copy.key"
    colocated.write_bytes(key.read_bytes()); colocated.chmod(0o600)
    with pytest.raises(ValueError, match="separate"):
        export([colocated])
    store.transition_case(session["user_id"], cases[0]["id"], 1, 1, "hold", "Preserve source and its older backups")
    assert export([key])[0]["hold"]
    append_record(journal, {"action": "delete_case", "owner": session["user_id"], "case_id": cases[1]["id"]})
    assert not export([key])[0]["restore_verified"]
    assert not export([key])[0]["physical_or_crypto_erasure_verified"]


def test_existing_or_colocated_outputs_traversal_links_and_public_key_permissions_are_refused(tmp_path):
    store, _, _, journal = setup(tmp_path)
    archive, key, receipt = backup(tmp_path, store)
    before = {p: file_digest(p) for p in (archive, key, receipt)}
    with pytest.raises(FileExistsError):
        encrypted.create_encrypted_backup(store.path, archive, key, receipt)
    with pytest.raises(ValueError, match="separate"):
        encrypted.create_encrypted_backup(store.path, tmp_path / "backups/other.recase", tmp_path / "backups/other.key", tmp_path / "backups/other.json")
    with pytest.raises(ValueError, match="traversal"):
        encrypted.create_encrypted_backup(store.path, tmp_path / "backups/../backups/other.recase", tmp_path / "keys/other.key", tmp_path / "backups/other.json")
    linked = tmp_path / "keys/linked.key"
    linked.symlink_to(key)
    with pytest.raises(OSError):
        encrypted.verify_encrypted_backup(receipt, linked, journal, tmp_path / "link", tmp_path / "link.json")
    hard = tmp_path / "keys/hard.key"
    os.link(key, hard)
    try:
        with pytest.raises(PermissionError):
            encrypted.verify_encrypted_backup(receipt, key, journal, tmp_path / "hard", tmp_path / "hard.json")
    finally:
        hard.unlink()  # Newly created test alias only; original key retained.
    key.chmod(0o644)
    try:
        with pytest.raises(PermissionError):
            encrypted.verify_encrypted_backup(receipt, key, journal, tmp_path / "public", tmp_path / "public.json")
    finally:
        key.chmod(0o600)
    assert all(file_digest(p) == value for p, value in before.items())
    assert not (tmp_path / "keys/other.key").exists()


def test_memory_and_backward_clock_limits_fail_before_any_output_is_created(tmp_path, monkeypatch):
    store, _, _, _ = setup(tmp_path)
    monkeypatch.setattr(encrypted, "MAX_BYTES", 1024)
    with pytest.raises(RuntimeError, match="budget"):
        backup(tmp_path, store)
    assert not list((tmp_path / "keys").iterdir()) and not list((tmp_path / "backups").iterdir())
    monkeypatch.setattr(encrypted, "MAX_BYTES", 128 * 1024 * 1024)
    clock = iter(("2030-01-01T00:00:00Z", "2029-12-31T00:00:00Z"))
    monkeypatch.setattr(encrypted, "utc_now", lambda: next(clock))
    with pytest.raises(RuntimeError, match="clock"):
        backup(tmp_path, store)
    assert not list((tmp_path / "keys").iterdir()) and not list((tmp_path / "backups").iterdir())


@pytest.mark.parametrize("changed", ["journal", "key"])
def test_concurrent_input_change_after_decryption_never_creates_a_pass_proof(tmp_path, monkeypatch, changed):
    store, _, _, journal = setup(tmp_path)
    archive, key, receipt = backup(tmp_path, store)
    original = encrypted.apply_deletions
    key_before, archive_before = key.read_bytes(), file_digest(archive)

    def change_during_restore(*args, **kwargs):
        result = original(*args, **kwargs)
        if changed == "journal":
            append_record(journal, {"action": "initialize", "scope": "concurrent synthetic fixture"})
        else:
            key.write_bytes(bytes([key_before[0] ^ 1]) + key_before[1:])
        return result

    monkeypatch.setattr(encrypted, "apply_deletions", change_during_restore)
    try:
        with pytest.raises(RuntimeError, match="verification failed"):
            verify(tmp_path, receipt, key, journal)
        assert not (tmp_path / "verified.json").exists()
        assert (tmp_path / "verified/restored.db").is_file()  # Preserve failed private scratch for diagnosis.
        assert file_digest(archive) == archive_before
    finally:
        key.write_bytes(key_before)
