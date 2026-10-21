"""Offline, read-only DB comparison before a release switch. Never switch or erase.

Hold the application's maintenance locks. New empty lock sidecars may be created;
    main database bytes, deletion journals, sessions and code are never changed.
    SQLite may create/update its own WAL/SHM read-coordination sidecars.
"""
import ast
import fcntl
import json
import os
import re
import sqlite3
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath
from itertools import chain

from recase.encrypted_backups import absolute_path, private_directory, private_new, read_private, require_operator
from recase.ledger import digest, file_digest, read_ledger, utc_now
from recase.lifecycle import CORE_COLUMNS
from recase.operations_drill import regular_private, save_private
from recase.store import Store

MAX_ROWS = 100_000
MAX_ROW_BYTES = 8 * 1024 * 1024
MAX_CONTENT_BYTES = 64 * 1024 * 1024
LIFECYCLE = {"case_lifecycle": {"case_id", "created", "closed", "hold", "data_class", "revision"},
             "case_lifecycle_events": {"case_id", "revision", "action", "actor", "reason", "at"}}


def allowed_release_path(value):
    if not isinstance(value, str) or len(value) > 512 or "\\" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        return False
    if re.fullmatch(r"backend/(recase|scripts|evaluation|training)/[A-Za-z_][A-Za-z0-9_]*\.py", value):
        return True
    if value in {"backend/training/train_mlx.sh", "docs/schemas/analysis_result.schema.json", "data/practice/v1/cases.json"}:
        return True
    if value in {"backend/requirements.txt", "backend/requirements-mac.txt", "backend/requirements-app.txt", "backend/requirements-lock-macos-arm64.txt"}:
        return True
    if value == "frontend/dist/index.html":
        return True
    return (value.startswith(("frontend/dist/assets/", "frontend/public/assets/"))
            and path.suffix.lower() in {".js", ".css", ".webp", ".avif", ".svg", ".png", ".jpg", ".jpeg", ".woff2"}
            and all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in path.parts))


def verify_stage(manifest_path, release_root):
    manifest_path = absolute_path(manifest_path)
    info = manifest_path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024 * 1024
            or not publisher_file(info) or any(p.is_symlink() for p in manifest_path.parents)):
        raise PermissionError("TRUSTED_RELEASE_MANIFEST_REQUIRED")
    manifest = json.loads(manifest_path.read_bytes())
    root = absolute_path(release_root)
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError("RELEASE_SYMLINK_REFUSED")
    if (not isinstance(manifest, dict) or manifest.get("format") != "recase-local-release-v2"
            or type(manifest.get("writable_schema_version")) is not int or manifest["writable_schema_version"] != 2
            or not isinstance(manifest.get("files"), list) or not 1 <= len(manifest["files"]) <= 2000
            or manifest.get("file_count") != len(manifest["files"])):
        raise ValueError("KNOWN_RELEASE_MANIFEST_REQUIRED")
    seen, total = set(), 0
    for row in manifest["files"]:
        if not isinstance(row, dict) or not allowed_release_path(row.get("path")) or row["path"] in seen:
            raise ValueError("RELEASE_PATH_OR_DUPLICATE_REFUSED")
        if (type(row.get("bytes")) is not int or not 0 <= row["bytes"] <= 16 * 1024 * 1024
                or not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"])):
            raise ValueError("BOUNDED_RELEASE_FILE_REQUIRED")
        path = root / row["path"]
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or not publisher_file(info) or info.st_nlink != 1
                or any(p.is_symlink() for p in path.parents)):
            raise PermissionError("PRIVATE_REGULAR_RELEASE_FILE_REQUIRED")
        total += info.st_size
        if total > 64 * 1024 * 1024 or info.st_size != row["bytes"] or file_digest(path) != row["sha256"]:
            raise ValueError("RELEASE_BYTES_CHANGED")
        seen.add(row["path"])
    required = {"backend/recase/api.py", "backend/recase/store.py", "backend/recase/lifecycle.py",
                "backend/recase/model.py", "backend/recase/mcp_client.py", "backend/recase/worker.py",
                "backend/requirements-lock-macos-arm64.txt", "frontend/dist/index.html"}
    if not required <= seen:
        raise ValueError("RELEASE_CORE_FILES_MISSING")
    if "backend/recase/practice.py" in seen and "data/practice/v1/cases.json" not in seen:
        raise ValueError("PRACTICE_DATA_REQUIRED")
    if "backend/recase/accounts.py" in seen or manifest.get("auth_contract"):
        if (manifest.get("auth_contract") != "account-password-v1"
                or not {"backend/recase/accounts.py", "backend/recase/auth_api.py", "backend/recase/account_state.py"} <= seen
                or "backend/recase/local_auth.py" in seen):
            raise ValueError("ACCOUNT_RELEASE_CONTRACT_REQUIRED")
    # Do not execute staged code to read its schema declaration.
    tree = ast.parse((root / "backend/recase/lifecycle.py").read_text())
    versions = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "SCHEMA_VERSION" for t in node.targets)
                and isinstance(node.value, ast.Constant)]
    if versions != [2]:
        raise ValueError("RELEASE_SCHEMA_DECLARATION_MISMATCH")
    for i, path in enumerate(chain((root,), root.rglob("*"))):
        if i > 6000:
            raise ValueError("RELEASE_TREE_BUDGET_EXCEEDED")
        info = path.lstat()
        if path.is_symlink() or path.is_file() and path.relative_to(root).as_posix() not in seen:
            raise ValueError("UNMANIFESTED_RELEASE_FILES_REFUSED")
        if path.is_dir() and (info.st_uid not in {0, os.geteuid()} or info.st_mode & 0o022):
            raise PermissionError("RELEASE_DIRECTORY_OWNERSHIP_REQUIRED")
    return manifest


def publisher_file(info):
    return (info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) in {0o400, 0o600}
            or info.st_uid == 0 and stat.S_IMODE(info.st_mode) in {0o444, 0o644})


@contextmanager
def offline(paths):
    with ExitStack() as stack:
        for path in sorted(set(paths)):
            regular_private(path, os.geteuid())
            if path.stat().st_nlink != 1:
                raise PermissionError("INDEPENDENT_DATABASE_REQUIRED")
            lock_path = path.with_name(path.name + ".server.lock")
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            stream = stack.enter_context(os.fdopen(fd, "r+b"))
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_size:
                raise PermissionError("KNOWN_MAINTENANCE_LOCK_REQUIRED")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("SERVER_RUNNING") from None
        yield


def read_snapshot(path):
    with Store(path, read_only=True).db() as db:
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ROW_BYTES)
        db.execute("BEGIN")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in {1, 2} or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("HEALTHY_KNOWN_DATABASE_REQUIRED")
        columns = {**CORE_COLUMNS, **(LIFECYCLE if version == 2 else {})}
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if tables != columns.keys() or db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone():
            raise ValueError("KNOWN_DATABASE_TABLE_CONTRACT_REQUIRED")
        data, count, size = {}, 0, 0
        for table, expected in columns.items():
            if {r[1] for r in db.execute(f"PRAGMA table_info({table})")} != expected:
                raise ValueError("KNOWN_DATABASE_COLUMN_CONTRACT_REQUIRED")
            fields = sorted(expected)
            data[table] = []
            for raw in db.execute(f"SELECT {','.join(fields)} FROM {table}"):
                row = dict(raw)
                count += 1
                size += len(json.dumps(row, ensure_ascii=False).encode())
                if count > MAX_ROWS or size > MAX_CONTENT_BYTES:
                    raise ValueError("TRANSITION_COMPARISON_BUDGET_EXCEEDED")
                data[table].append(row)
        case_ids = {r["id"] for r in data["cases"]}
        job_ids = {r["id"] for r in data["jobs"]}
        if any("case_id" in r and r["case_id"] not in case_ids for rows in data.values() for r in rows):
            raise ValueError("ORPHANED_CASE_DATA_REFUSED")
        if any(r["job_id"] not in job_ids for r in data["events"]):
            raise ValueError("ORPHANED_JOB_EVENTS_REFUSED")
        return version, data


def selected_rows(data, removed, deleted_jobs):
    result = {}
    for table, rows in data.items():
        if table == "sessions":
            continue
        keep = []
        for row in rows:
            discard = (table == "cases" and row["id"] in removed
                       or "case_id" in row and row["case_id"] in removed
                       or table == "events" and row["job_id"] in deleted_jobs
                       or table == "audit" and row["resource"] in removed | deleted_jobs)
            if not discard:
                keep.append(row)
        result[table] = keep
    return result


def row_map(table, rows):
    fields = ("case_id", "revision") if table == "case_lifecycle_events" else ("case_id",) if table == "case_lifecycle" else ("id",)
    return {tuple(r[k] for k in fields): digest(r) for r in rows}


def restore_hold_only(before, after, events):
    stable = {"case_id", "created", "closed", "data_class"}
    return (all(before[k] == after[k] for k in stable) and before["hold"] == 0 and after["hold"] == 1
            and after["revision"] == before["revision"] + 1
            and any(e["case_id"] == after["case_id"] and e["revision"] == after["revision"]
                    and e["action"] == "restore_hold" and e["actor"] == "local_restore"
                    and e["reason"] == "Restored data requires a fresh retention review" for e in events))


def check_transition(source, target, journal, manifest_path, release_root, report_path,
                     accounts_path=None, target_accounts_path=None):
    require_operator()
    source, target, journal = (absolute_path(p) for p in (source, target, journal))
    report_path = private_new(report_path)
    private_directory(report_path.parent)
    manifest = verify_stage(manifest_path, release_root)
    account_mode = manifest.get("auth_contract") == "account-password-v1"
    if account_mode != bool(accounts_path and target_accounts_path) or bool(accounts_path) != bool(target_accounts_path):
        raise ValueError("CURRENT_ACCOUNT_DATABASE_AND_ACCOUNT_RELEASE_REQUIRED")
    if accounts_path:
        accounts_path, target_accounts_path = (absolute_path(p) for p in (accounts_path, target_accounts_path))
        if not os.path.samefile(accounts_path, target_accounts_path):
            raise ValueError("ACCOUNT_DATABASE_ROLLBACK_REFUSED")
        if any(os.path.samefile(accounts_path, p) for p in (source, target, journal)):
            raise ValueError("SEPARATE_ACCOUNT_DATABASE_REQUIRED")
    manifest_sha = file_digest(manifest_path)
    read_private(journal, 16 * 1024 * 1024)
    journal_sha = file_digest(journal)
    events = [r["payload"] for r in read_ledger(journal) if r["payload"].get("action") == "delete_case"]
    if any(not isinstance(e.get(k), str) or not e[k] for e in events for k in ("owner", "case_id")):
        raise ValueError("VALID_DELETION_OWNERS_REQUIRED")
    removed = {e["case_id"] for e in events}
    with ExitStack() as stack:
        stack.enter_context(offline([source, target]))
        if accounts_path:
            from recase.account_state import account_lock, account_snapshot, validate_owners
            stack.enter_context(account_lock(accounts_path, exclusive=True))
            _, account_rows, account_commitment = account_snapshot(accounts_path)
        before = {p: file_digest(p) for p in {source, target}}
        source_version, old = read_snapshot(source)
        target_version, new = read_snapshot(target)
        if target_version != 2:
            raise ValueError("TARGET_SCHEMA_INCOMPATIBLE_WITH_RELEASE")
        if any(r["status"] in {"QUEUED", "RUNNING"} for d in (old, new) for r in d["jobs"]):
            raise ValueError("ACTIVE_JOBS_REQUIRE_OPERATOR_DIAGNOSIS")
        for event in events:
            if any(r["id"] == event["case_id"] and r["owner"] != event["owner"] for d in (old, new) for r in d["cases"]):
                raise ValueError("DELETION_OWNER_MISMATCH")
        deleted_jobs = {r["id"] for d in (old, new) for r in d["jobs"] if r["case_id"] in removed}
        current, proposed = (selected_rows(d, removed, deleted_jobs) for d in (old, new))
        account_checks = None
        if accounts_path:
            account_checks = {"source": validate_owners(current, account_rows), "target": validate_owners(proposed, account_rows),
                              "current_account_state_sha256": account_commitment, "same_current_accounts": True,
                              "old_credentials_roles_or_versions_restored": False,
                              "browser_sessions_require_process_restart": True}
        # Refuse resurrection in every linked table, including events/audit.
        if any(len(new[t]) != len(proposed[t]) for t in proposed):
            raise ValueError("TARGET_STILL_CONTAINS_TOMBSTONED_DATA")
        checks = {}
        for table, rows in current.items():
            expected, actual = row_map(table, rows), row_map(table, proposed[table])
            missing = [key for key, value in expected.items() if actual.get(key) != value]
            if table == "case_lifecycle" and missing:
                originals = {r["case_id"]: r for r in rows}
                targets = {r["case_id"]: r for r in proposed[table]}
                missing = [key for key in missing if key[0] not in targets or not restore_hold_only(
                    originals[key[0]], targets[key[0]], new["case_lifecycle_events"])]
            if missing:
                raise ValueError("MISSING_OR_CHANGED_CURRENT_ROWS:" + table)
            checks[table] = {"current_rows_preserved": len(expected), "target_rows": len(actual), "source_rows_sha256": digest(sorted(expected.values()))}
        if source_version == 1:
            original_ids = {r["id"] for r in current["cases"]}
            history = [r for r in new["case_lifecycle"] if r["case_id"] in original_ids]
            if (len(history) != len(original_ids) or any(r["created"] is not None or r["closed"] is not None
                    or r["data_class"] != "unclassified" or r["hold"] != 1 for r in history)):
                raise ValueError("LEGACY_HISTORY_MUST_REMAIN_UNKNOWN_AND_HELD")
        same_db = os.path.samefile(source, target)
        if not same_db and new["sessions"]:
            raise ValueError("COPIED_DATABASE_SESSIONS_MUST_BE_REVOKED")
        if file_digest(journal) != journal_sha or file_digest(manifest_path) != manifest_sha or any(file_digest(p) != sha for p, sha in before.items()):
            raise RuntimeError("TRANSITION_INPUTS_CHANGED")
        verify_stage(manifest_path, release_root)
        if accounts_path and account_snapshot(accounts_path)[2] != account_commitment:
            raise RuntimeError("CURRENT_ACCOUNTS_CHANGED")
        report = {"format": "database-release-transition-v1", "status": "PASS", "checked_at": utc_now(),
                  "worker_uid": os.getuid(), "worker_euid": os.geteuid(), "source_schema": source_version,
                  "target_schema": target_version, "same_database_code_switch": same_db, "checks": checks,
                  "current_journal_sha256": journal_sha, "release_manifest_sha256": manifest_sha,
                  "case_text_or_credentials_exported": False, "database_or_journal_mutations": 0,
                  "note": "Offline main-DB comparison only; lock and SQLite WAL/SHM coordination sidecars may be created. No deployment, model, UID499 access or erasure proof."}
        if account_checks:
            report["account_checks"] = account_checks
            report["note"] = "Offline cases and current account state checked; account rollback refused. Process restart must revoke in-memory sessions. No deployment or live-service proof."
        report["report_sha256"] = digest(report)
        save_private(report_path, report)
        return report
