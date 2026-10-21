"""New quarantined identities, fresh credentials, explicit local operator review.

Never overwrite a current account database or restore historical credentials or
roles. The quarantine schema is refused by the web app until a separate seal.
"""
import json
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

from recase.accounts import check_password, normalize_email, password_hash
from recase.account_backups import authenticated_account_image
from recase.account_state import (ACCOUNT_COLUMNS, ACCOUNT_TABLE_SQL, MAX_ACCOUNT_BYTES,
                                  account_lock, account_snapshot, read_account_rows)
from recase.encrypted_backups import absolute_path, private_directory, private_new, read_private, require_operator, sha_bytes
from recase.ledger import append_locked, append_record, digest, file_digest, locked_records, utc_now
from recase.operations_drill import save_private

QUARANTINE_VERSION = 9001
PROOF_FORMAT = "recase-identity-recovery-quarantine-v1"


def stage_identities(manifest, key_directory, target, proof):
    require_operator()
    manifest, key_directory = absolute_path(manifest), absolute_path(key_directory)
    target, proof = private_new(target), private_new(proof)
    private_directory(target.parent)
    private_directory(proof.parent)
    if target == proof:
        raise ValueError("SEPARATE_RECOVERY_PROOF_REQUIRED")
    ledger = private_new(proof.with_name(proof.stem + ".actions.jsonl"))
    pair, image, key = authenticated_account_image(manifest, key_directory)
    manifest_sha = file_digest(manifest)
    # Earlier WAL account images cannot be deserialized safely in memory. Refuse
    # those without writing old credentials. New backups use portable SQLite.
    if image[:16] != b"SQLite format 3\x00" or image[18:20] != b"\x01\x01":
        raise ValueError("PORTABLE_ACCOUNT_IMAGE_REQUIRED_NO_HEADER_PATCHING")
    with closing(sqlite3.connect(":memory:")) as db:
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ACCOUNT_BYTES)
        db.deserialize(image)
        db.row_factory = sqlite3.Row
        rows = read_account_rows(db)
    if digest(rows) != pair["header"]["account_state_sha256"]:
        raise ValueError("AUTHENTICATED_ACCOUNT_ROW_COMMITMENT_MISMATCH")
    if any(normalize_email(r["email"]) != r["email"] for r in rows):
        raise ValueError("CANONICAL_RECOVERY_EMAIL_REQUIRED")
    identities = [{k: r[k] for k in ("id", "email", "name", "created")} for r in rows]
    staged = [{**r, "role": "user", "enabled": 0, "credential_version": r["credential_version"] + 1,
               "password_hash": "scrypt$32768$8$3$" + secrets.token_hex(16) + "$" + secrets.token_hex(32)} for r in rows]
    # No bytes from the historical SQLite image/password verifiers reach disk.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    with account_lock(target, exclusive=True), closing(sqlite3.connect(target)) as db, db:
        db.execute(ACCOUNT_TABLE_SQL)
        db.executemany("INSERT INTO accounts VALUES(?,?,?,?,?,?,?,?)", [[r[k] for k in ACCOUNT_COLUMNS] for r in staged])
        db.execute("PRAGMA user_version=" + str(QUARANTINE_VERSION))
    _, actual, commitment = account_snapshot(target, (QUARANTINE_VERSION,))
    if digest(actual) != digest(staged):
        raise RuntimeError("STAGED_IDENTITIES_CHANGED_PRESERVE_PARTIAL_OUTPUTS")
    if (file_digest(manifest) != manifest_sha or authenticated_account_image(manifest, key_directory)[2] != key):
        raise RuntimeError("BACKUP_CHANGED_NO_RECOVERY_PASS_PROOF")
    info = target.stat()
    record = {"format": PROOF_FORMAT, "status": "QUARANTINED_NOT_DEPLOYABLE", "created_at": utc_now(),
              "target": str(target), "target_device": info.st_dev, "target_inode": info.st_ino,
              "actions_ledger": str(ledger), "manifest_sha256": manifest_sha,
              "identity_count": len(staged), "identity_commitment": digest(identities),
              "initial_state_sha256": commitment, "quarantine_schema": QUARANTINE_VERSION,
              "all_disabled": True, "all_roles_user": True, "historical_password_hashes_written": False,
              "old_admin_roles_restored": False, "operator_identity_confirmation": "PENDING",
              "automatic_deployment_or_credential_reactivation": False}
    record["proof_sha256"] = digest(record)
    append_record(ledger, {"action": "recovery_staged", "proof_sha256": record["proof_sha256"], "state_sha256": commitment})
    save_private(proof, record)
    return record


def load_recovery(path, target):
    require_operator()
    path, target = absolute_path(path), absolute_path(target)
    private_directory(path.parent)
    private_directory(target.parent)
    proof = json.loads(read_private(path, 1024 * 1024))
    if (proof.get("format") != PROOF_FORMAT or proof.get("proof_sha256") != digest({k:v for k,v in proof.items() if k != "proof_sha256"})
            or proof.get("target") != str(target) or proof.get("quarantine_schema") != QUARANTINE_VERSION):
        raise ValueError("RECOVERY_PROOF_REQUIRED")
    read_private(target, MAX_ACCOUNT_BYTES)
    info = target.stat()
    if (info.st_dev, info.st_ino) != (proof["target_device"], proof["target_inode"]):
        raise ValueError("RECOVERY_DATABASE_REPLACED")
    ledger = absolute_path(proof["actions_ledger"])
    if ledger != path.with_name(path.stem + ".actions.jsonl"):
        raise ValueError("RECOVERY_LEDGER_PATH_CHANGED")
    read_private(ledger, 4 * 1024 * 1024)
    return proof, ledger


def locked_state(target, proof, records):
    if not records or records[0]["payload"].get("proof_sha256") != proof["proof_sha256"]:
        raise ValueError("RECOVERY_LEDGER_PROOF_MISMATCH")
    last = records[-1]["payload"]
    if last.get("action") not in {"recovery_staged", "activation_completed"}:
        raise RuntimeError("INTERRUPTED_OR_SEALED_RECOVERY_REQUIRES_OPERATOR_AUDIT")
    _, rows, commitment = account_snapshot(target, (QUARANTINE_VERSION,))
    if last.get("state_sha256") != commitment or any(r["role"] != "user" for r in rows):
        raise ValueError("RECOVERY_STATE_CHANGED_OUTSIDE_REVIEW")
    return rows, commitment


def activate_user(target, proof_path, email, expected_user_id, new_password, reason):
    """Called only after TTY identity confirmation; tests use synthetic identities."""
    target, proof_path = absolute_path(target), absolute_path(proof_path)
    proof, ledger = load_recovery(proof_path, target)
    email = normalize_email(email)
    check_password(new_password)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise ValueError("IDENTITY_CONFIRMATION_REASON_REQUIRED")
    encoded = password_hash(new_password)
    with account_lock(target, exclusive=True), locked_records(ledger, create=True) as (stream, records):
        rows, before = locked_state(target, proof, records)
        user = next((r for r in rows if r["id"] == expected_user_id and r["email"] == email), None)
        if not user or user["enabled"]:
            raise ValueError("EXACT_DISABLED_RECOVERY_IDENTITY_REQUIRED")
        user.update(password_hash=encoded, enabled=1, credential_version=user["credential_version"] + 1)
        after = digest(rows)
        intent = append_locked(stream, records, {"action": "activation_intent", "user_id_sha256": digest(expected_user_id),
                    "previous_state_sha256": before, "next_state_sha256": after, "operator_uid": os.geteuid(),
                    "confirmation_source": "local_operator_identity_check", "reason": reason.strip()})
        with closing(sqlite3.connect(target)) as db, db:
            db.execute("UPDATE accounts SET password_hash=?,enabled=1,credential_version=credential_version+1 WHERE id=? AND email=? AND enabled=0 AND role='user'",
                       (encoded, expected_user_id, email))
        if account_snapshot(target, (QUARANTINE_VERSION,))[2] != after:
            raise RuntimeError("ACTIVATION_INCOMPLETE_PRESERVE_FOR_OPERATOR_AUDIT")
        append_locked(stream, records, {"action": "activation_completed", "intent_sha256": intent["sha256"], "state_sha256": after})
        return {"status": "IDENTITY_ACTIVATED_IN_QUARANTINE", "role": "user", "web_deployable": False}


def seal_recovery(target, proof_path, report_path, held_user_ids):
    """Explicit TTY acknowledgement keeps every unverified identity disabled."""
    target, proof_path, report_path = absolute_path(target), absolute_path(proof_path), private_new(report_path)
    private_directory(report_path.parent)
    proof, ledger = load_recovery(proof_path, target)
    with account_lock(target, exclusive=True), locked_records(ledger, create=True) as (stream, records):
        rows, before = locked_state(target, proof, records)
        held = {r["id"] for r in rows if not r["enabled"]}
        if set(held_user_ids) != held:
            raise ValueError("EXACT_HELD_IDENTITIES_ACKNOWLEDGEMENT_REQUIRED")
        intent = append_locked(stream, records, {"action": "seal_intent", "state_sha256": before,
                             "held_identity_sha256": sorted(digest(i) for i in held), "operator_uid": os.geteuid()})
        with closing(sqlite3.connect(target)) as db, db:
            db.execute("PRAGMA user_version=1")
        if account_snapshot(target)[2] != before:
            raise RuntimeError("SEAL_INCOMPLETE_REQUIRES_OPERATOR_AUDIT")
        last = append_locked(stream, records, {"action": "recovery_sealed", "intent_sha256": intent["sha256"], "state_sha256": before})
        result = {"format": "recase-identity-recovery-seal-v1", "status": "LOCAL_REVIEW_SEALED_NOT_DEPLOYED",
                  "checked_at": utc_now(), "proof_sha256": proof["proof_sha256"], "account_state_sha256": before,
                  "actions_head_sha256": last["sha256"], "active_user_count": len(rows)-len(held), "held_user_count": len(held),
                  "admin_count": 0, "historical_password_hashes_restored": False, "deployment_executed": False,
                  "case_recovery": "Use current journal and separately verify case ownership/content before deployment"}
        result["seal_sha256"] = digest(result)
        save_private(report_path, result)
        return result
