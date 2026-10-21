"""Backup a read-only source; exercise deletion/recovery on new private copies only.

This module's source can be sent to the isolated interpreter after its hash and
the deployed modules are checked. It does not load models or serve HTTP.
"""
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def regular_private(path, expected_uid):
    path = Path(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != expected_uid
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise PermissionError("Expected a regular service-owned mode0600 file")
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("Symlink ancestors are not allowed")
    return info


def save_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


def _run(backend, source, journal, destination, expected_uid):
    if expected_uid == 0 or os.getuid() != expected_uid or os.geteuid() != expected_uid:
        raise PermissionError("The drill must execute as the expected nonroot service account")
    sys.dont_write_bytecode = True
    backend, source, journal, out = (Path(p).absolute() for p in (backend, source, journal, destination))
    source_info = regular_private(source, expected_uid)
    regular_private(journal, expected_uid)
    if out.exists() or out.is_symlink() or any(p.is_symlink() for p in out.parents):
        raise FileExistsError("A new private drill directory without symlinks is required")
    if source.is_relative_to(out) or journal.is_relative_to(out) or source == journal:
        raise ValueError("Production inputs must be outside the new drill directory")
    wal = Path(str(source) + "-wal")
    estimated_bytes = source_info.st_size + (wal.stat().st_size if wal.exists() else 0)
    disk_budget = 6 * estimated_bytes + 16 * 1024 * 1024
    if shutil.disk_usage(source.parent).free < disk_budget:
        raise RuntimeError("Insufficient free disk space for isolated backup/copy validation")
    sys.path.insert(0, str(backend))
    from recase.store import Store
    from recase.ledger import digest, read_ledger
    from recase.retention import apply_deletions, delete_case
    from recase import store as store_module, ledger as ledger_module, retention as retention_module, lifecycle as lifecycle_module
    modules = {m.__name__: Path(m.__file__).resolve() for m in (store_module, ledger_module, retention_module, lifecycle_module)}
    if any(p.parent != (backend / "recase").resolve() for p in modules.values()):
        raise ValueError("Only the explicitly selected deployment modules may execute")
    source_store = Store(source, read_only=True)
    # Validate the independent current journal BEFORE creating a backup/output.
    production_entries = read_ledger(journal)
    journal_before = sha(journal)
    with source_store.db() as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Source database integrity failure")
        source_cases = db.execute("SELECT count(*) FROM cases").fetchone()[0]
        if source_cases < 1:
            raise ValueError("A populated real service database is required")
        source_version = db.execute("PRAGMA user_version").fetchone()[0]
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    # This is the only live-database operation: SQLite's consistent backup API
    # through mode=ro. All mutations below address the new scratch directory.
    snapshot = source_store.backup(out / "live-backup.db")
    snapshot_sha = sha(snapshot)
    with Store(snapshot, read_only=True).db() as db:
        # Counts come from the consistent snapshot, not two different live moments.
        source_cases = db.execute("SELECT count(*) FROM cases").fetchone()[0]
        source_version = db.execute("PRAGMA user_version").fetchone()[0]
    Store(snapshot, read_only=True).backup(out / "source-copy.db")
    baseline_ledger = out / "production-journal-copy.jsonl"
    baseline_ledger.write_bytes(journal.read_bytes())
    baseline_ledger.chmod(0o600)
    if sha(baseline_ledger) != journal_before or sha(journal) != journal_before:
        raise RuntimeError("Independent journal changed while taking the backup; preserve this run and retry with a new plan")
    work_ledger = out / "drill-deletions.jsonl"
    work_ledger.write_bytes(baseline_ledger.read_bytes())
    work_ledger.chmod(0o600)
    scratch_migration = lifecycle_module.migrate_v1(out / "source-copy.db", out / "schema1-scratch-rollback.db") if source_version == 1 else None
    work = Store(out / "source-copy.db")
    # Create the target only in the scratch copy, never delete a production ID.
    session = work.new_demo()
    victim, survivor = work.cases(session["user_id"])
    with source_store.db() as db:
        if db.execute("SELECT count(*) FROM cases WHERE id IN (?,?)", (victim["id"], survivor["id"])).fetchone()[0]:
            raise RuntimeError("Scratch fixture identifier collision")
    job = work.create_job(session["user_id"], victim["id"], 1, {"backend": "operations_fixture_no_model"})
    before_delete = work.backup(out / "before-delete.db")
    before_delete_sha = sha(before_delete)
    result = delete_case(work.path, work_ledger, session["user_id"], victim["id"])
    if result["status"] != "PASS":
        raise RuntimeError("Scratch deletion did not pass")
    # Refuse a missing/corrupt journal before touching a restoration destination.
    missing_journal_refused = False
    try:
        read_ledger(out / "missing-journal.jsonl")
    except FileNotFoundError:
        missing_journal_refused = True
    restored_path = out / "restored.db"
    Store(before_delete, read_only=True).backup(restored_path)
    replay = apply_deletions(restored_path, work_ledger, revoke_all_sessions=True)
    replay_again = apply_deletions(restored_path, work_ledger, revoke_all_sessions=True)
    recovered_jobs = Store(restored_path).recover()
    existing_target_refused = False
    try:
        source_store.backup(snapshot)
    except FileExistsError:
        existing_target_refused = True
    invariants = {}
    for name, path in (("deleted_copy", work.path), ("restored_copy", restored_path)):
        with Store(path, read_only=True).db() as db:
            invariants[name] = {
                "target_case_absent": db.execute("SELECT count(*) FROM cases WHERE id=?", (victim["id"],)).fetchone()[0] == 0,
                "target_evidence_absent": db.execute("SELECT count(*) FROM evidence WHERE case_id=?", (victim["id"],)).fetchone()[0] == 0,
                "target_claims_absent": db.execute("SELECT count(*) FROM claims WHERE case_id=?", (victim["id"],)).fetchone()[0] == 0,
                "target_job_absent": db.execute("SELECT count(*) FROM jobs WHERE id=?", (job["id"],)).fetchone()[0] == 0,
                "target_events_absent": db.execute("SELECT count(*) FROM events WHERE job_id=?", (job["id"],)).fetchone()[0] == 0,
                "surviving_case_preserved": db.execute("SELECT count(*) FROM cases WHERE id=?", (survivor["id"],)).fetchone()[0] == 1,
                "fixture_owner_sessions_revoked": db.execute("SELECT count(*) FROM sessions WHERE user_id=?", (session["user_id"],)).fetchone()[0] == 0,
                "integrity_ok": db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "owner_and_mode_0600": path.stat().st_uid == expected_uid and stat.S_IMODE(path.stat().st_mode) == 0o600,
            }
            if name == "restored_copy":
                invariants[name]["all_backed_up_sessions_revoked"] = db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
                invariants[name]["production_case_count_preserved"] = db.execute("SELECT count(*) FROM cases").fetchone()[0] == source_cases + 1
                invariants[name]["no_pending_jobs_after_recovery"] = db.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[0] == 0
    current_info = source.lstat()
    checks = {
        "actual_worker_nonroot_uid": os.getuid() == expected_uid,
        "disk_budget_checked_before_backup": True,
        "source_opened_read_only": source_store.read_only is True,
        "same_live_database_inode": (current_info.st_dev, current_info.st_ino) == (source_info.st_dev, source_info.st_ino),
        "production_journal_bytes_unchanged": sha(journal) == journal_before,
        "production_journal_copy_unchanged": sha(baseline_ledger) == journal_before,
        "live_backup_bytes_preserved": sha(snapshot) == snapshot_sha,
        "before_delete_backup_bytes_preserved": sha(before_delete) == before_delete_sha,
        "missing_journal_refused": missing_journal_refused,
        "existing_backup_destination_refused": existing_target_refused,
        "new_tombstone_replayed": replay["deleted_cases_replayed"] >= 1,
        "replay_idempotent": replay_again["deleted_cases_replayed"] == 0,
        "all_copy_invariants": all(all(v.values()) for v in invariants.values()),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "worker_uid": os.getuid(), "worker_euid": os.geteuid(),
              "source_schema": source_version, "source_case_count_at_snapshot": source_cases,
              "scratch_schema_migration": scratch_migration,
              "restored_jobs_marked_server_restarted": recovered_jobs,
              "production_journal_records": len(production_entries), "checks": checks, "invariants": invariants,
              "executed_module_hashes": {name: sha(path) for name, path in modules.items()},
              "live_backup_sha256": snapshot_sha, "fixture_case_digest": digest(victim["id"]),
              "artifacts": str(out), "model_calls": 0, "training_runs": 0, "production_delete_calls": 0,
              "scope": "Read-only live SQLite backup; new synthetic target deleted/restored only in private copies",
              "backup_bytes_erased": False, "physical_erasure_verified": False,
              "automatic_retention": "DISABLED_MANUAL_OPERATOR_POLICY"}
    save_private(out / "report.json", report)
    if report["status"] != "PASS":
        raise RuntimeError("Operations-copy invariants failed; preserve the drill artifacts")
    return report


def run(backend, source, journal, destination, expected_uid):
    previous_umask = os.umask(0o077)
    try:
        return _run(backend, source, journal, destination, expected_uid)
    finally:
        os.umask(previous_umask)
