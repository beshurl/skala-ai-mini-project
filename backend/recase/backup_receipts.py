"""Local backup receipts and restore checks; no backup disposal or key erasure."""
import json
import os
import shutil
import uuid
from pathlib import Path

from recase.ledger import digest, file_digest, read_ledger, utc_now
from recase.lifecycle import inventory, migrate_v1
from recase.operations_drill import regular_private, save_private
from recase.retention import apply_deletions, deletion_events
from recase.retention_schedule import instant
from recase.store import Store


def private_json(path):
    path = Path(path).absolute()
    info = regular_private(path, os.geteuid())
    if info.st_size > 1024 * 1024 or info.st_nlink != 1:
        raise ValueError("Bounded independent private JSON required")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def new_path(path):
    path = Path(path).absolute()
    if path.exists() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise FileExistsError("Independent new destination without symlinks required")
    return path


def create_backup(source, target, receipt_path):
    source = Path(source).absolute()
    regular_private(source, os.geteuid())
    target, receipt_path = new_path(target), new_path(receipt_path)
    if target == receipt_path:
        raise ValueError("Separate backup and receipt destinations required")
    wal = Path(str(source) + "-wal")
    estimated = source.stat().st_size + (wal.stat().st_size if wal.exists() else 0)
    if shutil.disk_usage(target.parent).free < estimated + 16 * 1024 * 1024:
        raise RuntimeError("Insufficient disk space for a new consistent backup")
    started = utc_now()
    Store(source, read_only=True).backup(target)
    snapshot = inventory(target)  # Read the consistent backup, not the changing source.
    receipt = {"format": "local-backup-receipt-v1", "backup_id": uuid.uuid4().hex,
               "created_at": utc_now(), "started_at": started, "creation_clock": "explicit_backup_completion_UTC",
               "backup_path": str(target), "backup_sha256": file_digest(target),
               "source_schema_version": snapshot["schema_version"],
               "case_identities": [r["identity_sha256"] for r in snapshot["cases"]],
               "data_class": "synthetic_fixture" if snapshot["cases"] and all(r["data_class"] == "synthetic_fixture" for r in snapshot["cases"]) else "unclassified",
               "initial_hold": any(r["hold"] for r in snapshot["cases"]),
               "restore_verified": False, "physical_or_crypto_erasure_verified": False}
    receipt["receipt_sha256"] = digest(receipt)
    if instant(receipt["created_at"]) < instant(started):
        raise RuntimeError("Backup completion clock moved backwards; preserve unreceipted backup")
    save_private(receipt_path, receipt)
    return {"status": "PASS", "receipt_sha256": file_digest(receipt_path),
            "backup_sha256": receipt["backup_sha256"], "deletions_executed": 0}


def read_receipt(path):
    receipt = private_json(path)
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if receipt.get("format") != "local-backup-receipt-v1" or digest(body) != receipt.get("receipt_sha256"):
        raise ValueError("Backup receipt integrity failure")
    identities = receipt.get("case_identities")
    if (receipt.get("source_schema_version") not in {1, 2}
            or receipt.get("data_class") not in {"synthetic_fixture", "unclassified"}
            or type(receipt.get("initial_hold")) is not bool
            or not isinstance(identities, list) or len(identities) > 1000
            or any(not isinstance(i, str) or len(i) != 64 or any(c not in "0123456789abcdef" for c in i) for i in identities)
            or len(set(identities)) != len(identities)
            or not isinstance(receipt.get("backup_id"), str) or len(receipt["backup_id"]) != 32):
        raise ValueError("Invalid backup receipt metadata")
    if instant(receipt["created_at"]) < instant(receipt["started_at"]):
        raise ValueError("Invalid explicit backup timestamps")
    backup = Path(receipt["backup_path"])
    regular_private(backup, os.geteuid())
    if file_digest(backup) != receipt["backup_sha256"]:
        raise ValueError("Backup bytes changed since creation")
    return receipt, backup


def preserved_content(db, excluded_cases):
    """Hash stable case/evidence/claim rows and job inputs, without exporting text."""
    hashes = {}
    for table, fields in (("cases", "*"), ("evidence", "*"), ("claims", "*"),
                          ("jobs", "id,case_id,owner,version,snapshot,model")):
        rows = db.execute(f"SELECT {fields} FROM {table} LIMIT 100001").fetchall()
        if len(rows) > 100000:
            raise ValueError("Backup content verification row budget exceeded")
        key = "id" if table == "cases" else "case_id"
        hashes[table] = digest(sorted([list(row) for row in rows if row[key] not in excluded_cases], key=lambda row: str(row)))
    return hashes


def verify_backup(receipt_path, journal, scratch, report_path):
    report_path, scratch = new_path(report_path), new_path(scratch)
    receipt, backup = read_receipt(receipt_path)
    receipt_sha = file_digest(receipt_path)
    journal = Path(journal).absolute()
    regular_private(journal, os.geteuid())
    if journal == backup or journal == Path(receipt_path).absolute() or report_path == scratch or report_path.is_relative_to(scratch):
        raise ValueError("Current independent deletion journal and separate destinations required")
    read_ledger(journal)
    journal_sha = file_digest(journal)
    if shutil.disk_usage(scratch.parent).free < 4 * backup.stat().st_size + 16 * 1024 * 1024:
        raise RuntimeError("Insufficient disk space for private restore verification")
    exclusions = {e["case_id"] for e in deletion_events(journal)}
    with Store(backup, read_only=True).db() as db:
        expected = preserved_content(db, exclusions)
    scratch.mkdir(mode=0o700)
    restored = Store(backup, read_only=True).backup(scratch / "restored.db")
    migration = None
    if receipt["source_schema_version"] == 1:
        migration = migrate_v1(restored, scratch / "schema1-rollback.db")
    replay = apply_deletions(restored, journal)
    recovered = Store(restored).recover()
    with Store(restored, read_only=True).db() as db:
        checks = {"integrity": db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                  "sessions_revoked": db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0,
                  "pending_jobs_cleared": db.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[0] == 0,
                  "surviving_content_preserved": expected == preserved_content(db, set()),
                  "restored_retention_held": db.execute("SELECT count(*) FROM case_lifecycle WHERE hold!=1").fetchone()[0] == 0}
    checks["backup_bytes_unchanged"] = file_digest(backup) == receipt["backup_sha256"]
    checks["receipt_unchanged"] = file_digest(receipt_path) == receipt_sha
    checks["current_journal_unchanged"] = file_digest(journal) == journal_sha
    if not all(checks.values()):
        raise RuntimeError("Backup restore verification failed; preserve scratch for diagnosis")
    report = {"format": "local-backup-verification-v1", "status": "PASS", "checked_at": utc_now(),
              "receipt_file_sha256": receipt_sha, "backup_sha256": receipt["backup_sha256"],
              "journal_sha256": journal_sha, "checks": checks, "replay": replay,
              "jobs_marked_server_restarted": recovered, "scratch_schema_migration": migration,
              "source_or_backup_deleted": False, "physical_or_crypto_erasure_verified": False,
              "trust_scope": "Local operator execution receipt; not resistant to malicious same-UID rewriting"}
    report["verification_sha256"] = digest(report)
    save_private(report_path, report)
    return report


def backup_inventory(receipt_paths, verification_paths, journal, case_inventory):
    if len(receipt_paths) > 1000 or len(verification_paths) > 1000:
        raise ValueError("Bounded backup inventory required")
    regular_private(Path(journal).absolute(), os.geteuid())
    read_ledger(journal)
    journal_sha = file_digest(journal)
    verifications = {}
    for path in verification_paths:
        report = private_json(path)
        if report.get("verification_sha256") != digest({k: v for k, v in report.items() if k != "verification_sha256"}):
            raise ValueError("Verification receipt integrity failure")
        verifications.setdefault(report.get("receipt_file_sha256"), []).append(report)
    held_cases = {r["identity_sha256"] for r in case_inventory["cases"] if r["hold"]}
    rows, seen = [], set()
    for path in receipt_paths:
        receipt, _ = read_receipt(path)
        identity = digest(["backup", receipt["backup_id"]])
        if identity in seen:
            raise ValueError("Duplicate backup receipt")
        seen.add(identity)
        verified = any(r.get("format") == "local-backup-verification-v1" and r.get("status") == "PASS"
            and r.get("backup_sha256") == receipt["backup_sha256"] and r.get("journal_sha256") == journal_sha
            and set(r.get("checks", {})) == {"integrity", "sessions_revoked", "pending_jobs_cleared", "surviving_content_preserved", "restored_retention_held", "backup_bytes_unchanged", "receipt_unchanged", "current_journal_unchanged"}
            and all(value is True for value in r["checks"].values())
            for r in verifications.get(file_digest(path), []))
        rows.append({"identity_sha256": identity, "data_class": receipt["data_class"], "created_at": receipt["created_at"],
                     "hold": receipt["initial_hold"] or bool(set(receipt["case_identities"]) & held_cases),
                     "restore_verified": verified, "verification_scope": "Current supplied journal hash and immutable backup bytes; preview only"})
    if file_digest(journal) != journal_sha:
        raise RuntimeError("Journal changed during inventory export")
    return rows
