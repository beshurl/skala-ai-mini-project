import fcntl
import gc
import hashlib
import json
from pathlib import Path

import pytest

from recase import release_validation as release
from recase.ledger import append_record, file_digest
from recase.lifecycle import migrate_v1
from recase.retention import apply_deletions
from recase.store import Store


def fixture(tmp_path, legacy=False):
    source = Store(tmp_path / "source.db")
    session = source.new_demo()
    case = source.cases(session["user_id"])[0]
    job = source.create_job(session["user_id"], case["id"], 1, {"backend": "synthetic_no_model"})
    source.set_status(session["user_id"], job["id"], "COMPLETED", result={"fixture": "Completed historical result must survive"})
    if legacy:
        with source.db() as db:
            db.execute("DROP TABLE case_lifecycle_events")
            db.execute("DROP TABLE case_lifecycle")
            db.execute("PRAGMA user_version=1")
    journal = tmp_path / "journal.jsonl"
    append_record(journal, {"action": "initialize", "scope": "new synthetic transition test"})
    root = tmp_path / "release"
    names = ["backend/recase/" + name + ".py" for name in ("api", "store", "lifecycle", "model", "mcp_client", "worker")]
    names += ["backend/requirements-lock-macos-arm64.txt", "frontend/dist/index.html"]
    entries = []
    for name in names:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_text("SCHEMA_VERSION = 2\n" if name.endswith("lifecycle.py") else "# private synthetic release test\n")
        p.chmod(0o600)
        entries.append({"path": name, "bytes": p.stat().st_size, "sha256": file_digest(p)})
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format": "recase-local-release-v2", "writable_schema_version": 2, "file_count": len(entries), "files": entries}))
    manifest.chmod(0o600)
    target = source.backup(tmp_path / "target.db")
    if legacy:
        migrate_v1(target, tmp_path / "schema1-rollback.db")
    apply_deletions(target, journal)
    return source, session, case, job, target, journal, manifest, root


def check(tmp_path, parts, name="verified", **overrides):
    source, _, _, _, target, journal, manifest, root = parts
    values = {"source": source.path, "target": target, "journal": journal, "manifest_path": manifest,
              "release_root": root, "report_path": tmp_path / f"{name}.json"}
    values.update(overrides)
    return release.check_transition(**values)


@pytest.mark.parametrize("legacy", [True, False])
def test_offline_upgrade_or_stronger_restore_hold_preserves_complete_current_rows(tmp_path, legacy):
    parts = fixture(tmp_path, legacy)
    before = {p: file_digest(p) for p in (parts[0].path, parts[4], parts[5], parts[6])}
    report = check(tmp_path, parts)
    assert report["status"] == "PASS" and report["source_schema"] == (1 if legacy else 2)
    assert report["checks"]["jobs"]["current_rows_preserved"] == 1
    assert report["checks"]["audit"]["current_rows_preserved"] > 0
    gc.collect()  # No delayed writable connection may checkpoint after PASS.
    assert all(file_digest(p) == value for p, value in before.items())
    assert parts[1]["token"] not in json.dumps(report) and parts[2]["title"] not in json.dumps(report)


def test_stale_copy_blocks_post_upgrade_data_loss_but_same_db_code_switch_keeps_writes(tmp_path):
    parts = fixture(tmp_path)
    source = parts[0]
    new_session = source.new_demo()
    case = source.cases(new_session["user_id"])[0]
    source.transition_case(new_session["user_id"], case["id"], 1, 1, "close", "Post-upgrade write must not disappear")
    before = {p: file_digest(p) for p in (source.path, parts[4])}
    with pytest.raises(ValueError, match="MISSING_OR_CHANGED_CURRENT_ROWS:cases"):
        check(tmp_path, parts, "stale")
    assert not (tmp_path / "stale.json").exists()
    same = check(tmp_path, parts, "same", target=source.path)
    assert same["same_database_code_switch"] and same["checks"]["cases"]["current_rows_preserved"] == 4
    assert all(file_digest(p) == value for p, value in before.items())


@pytest.mark.parametrize("table,sql", [
    ("jobs", "UPDATE jobs SET result='{}'"),
    ("evidence", "UPDATE evidence SET text='Changed historical evidence'"),
    ("case_lifecycle", "UPDATE case_lifecycle SET closed=1000"),
])
def test_changed_results_evidence_or_lifecycle_are_not_accepted_as_a_rollback(tmp_path, table, sql):
    parts = fixture(tmp_path)
    with Store(parts[4], read_only=False).db() as db:
        db.execute(sql)
    with pytest.raises(ValueError, match="MISSING_OR_CHANGED_CURRENT_ROWS:" + table):
        check(tmp_path, parts)
    assert not (tmp_path / "verified.json").exists()


def test_old_schema_copy_active_jobs_and_live_server_are_refused(tmp_path):
    parts = fixture(tmp_path)
    target = Store(parts[4])
    with target.db() as db:
        db.execute("PRAGMA user_version=1")
    with pytest.raises(ValueError, match="KNOWN_DATABASE_TABLE_CONTRACT|TARGET_SCHEMA_INCOMPATIBLE"):
        check(tmp_path, parts, "schema")
    with target.db() as db:
        db.execute("PRAGMA user_version=2")
    parts[0].create_job(parts[1]["user_id"], parts[2]["id"], 1, {"backend": "synthetic_no_model"})
    with pytest.raises(ValueError, match="ACTIVE_JOBS"):
        check(tmp_path, parts, "pending")
    lock = parts[0].path.with_name("source.db.server.lock")
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="SERVER_RUNNING"):
            check(tmp_path, parts, "running")


def test_current_tombstone_must_be_replayed_and_owner_must_match(tmp_path):
    parts = fixture(tmp_path)
    source, session, case, _, target, journal, _, _ = parts
    append_record(journal, {"action": "delete_case", "owner": session["user_id"], "case_id": case["id"]})
    with pytest.raises(ValueError, match="TOMBSTONED_DATA"):
        check(tmp_path, parts, "not-replayed")
    apply_deletions(target, journal)
    assert check(tmp_path, parts)["status"] == "PASS"
    append_record(journal, {"action": "delete_case", "owner": "wrong-owner", "case_id": source.cases(session["user_id"])[1]["id"]})
    with pytest.raises(ValueError, match="OWNER_MISMATCH"):
        check(tmp_path, parts, "wrong-owner")


def test_changed_or_unmanifested_code_refused_before_db_sidecars(tmp_path):
    parts = fixture(tmp_path)
    modified = parts[-1] / "backend/recase/api.py"
    modified.write_text("# changed\n")
    with pytest.raises(ValueError, match="RELEASE_BYTES_CHANGED"):
        check(tmp_path, parts)
    manifest = json.loads(parts[-2].read_text())
    row = next(r for r in manifest["files"] if r["path"] == "backend/recase/api.py")
    row.update(bytes=modified.stat().st_size, sha256=file_digest(modified))
    parts[-2].write_text(json.dumps(manifest))
    extra = parts[-1] / "backend/recase/unsigned.pyc"
    extra.write_bytes(b"not approved bytecode")
    with pytest.raises(ValueError, match="UNMANIFESTED"):
        check(tmp_path, parts)
    assert not parts[0].path.with_name("source.db.server.lock").exists()


def test_change_during_check_never_writes_a_pass_report(tmp_path, monkeypatch):
    parts = fixture(tmp_path)
    original = release.read_snapshot
    calls = []
    def change_after_snapshot(path):
        result = original(path)
        calls.append(path)
        if len(calls) == 2:
            append_record(parts[5], {"action": "initialize", "scope": "concurrent synthetic journal change"})
        return result
    monkeypatch.setattr(release, "read_snapshot", change_after_snapshot)
    with pytest.raises(RuntimeError, match="INPUTS_CHANGED"):
        check(tmp_path, parts)
    assert not (tmp_path / "verified.json").exists()
