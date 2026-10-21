"""Offline encrypted case/account pair; restore cases with CURRENT accounts only.

The encrypted account image is a held recovery artifact, never an automatic
credential/role restore. Losing the current account DB requires operator review.
"""
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from recase.account_state import MAX_ACCOUNT_BYTES, account_lock, account_snapshot, portable_account_image, validate_owners
from recase.encrypted_backups import (absolute_path, canonical, create_encrypted_backup, private_directory,
                                      private_new, read_private, require_operator, separate_key_directory,
                                      sha_bytes, verify_encrypted_backup, write_bytes)
from recase.ledger import digest, file_digest, read_ledger, utc_now
from recase.operations_drill import save_private
from recase.release_validation import offline, read_snapshot

PAIR_FORMAT = "recase-account-backup-pair-v1"
ACCOUNT_MAGIC = b"RECASE-HELD-ACCOUNT-SNAPSHOT-V1\n"


def create_pair(source, accounts, journal, directory, key_directory):
    require_operator()
    source, accounts, journal, directory, key_directory = (absolute_path(p) for p in (source, accounts, journal, directory, key_directory))
    private_new(directory)
    private_directory(directory.parent)
    private_directory(key_directory)
    if directory == key_directory or directory in key_directory.parents or key_directory in directory.parents:
        raise ValueError("SEPARATE_NON_NESTED_KEY_DIRECTORY_REQUIRED")
    if any(os.path.samefile(accounts, p) for p in (source, journal)):
        raise ValueError("SEPARATE_ACCOUNT_DATABASE_REQUIRED")
    journal_sha = sha_bytes(read_private(journal, 16 * 1024 * 1024))
    read_ledger(journal)
    with offline([source]), account_lock(accounts, exclusive=True):
        _, data = read_snapshot(source)
        if any(r["status"] in {"QUEUED", "RUNNING"} for r in data["jobs"]):
            raise ValueError("ACTIVE_JOBS_REQUIRE_OPERATOR_DIAGNOSIS")
        image, rows, commitment = account_snapshot(accounts)
        image = portable_account_image(rows)
        ownership = validate_owners(data, rows)
        directory.mkdir(mode=0o700)
        separate_key_directory(directory, key_directory)
        # Unique per-pair key names; no overwrite or old-key reuse.
        nonce, key = os.urandom(12), AESGCM.generate_key(bit_length=256)
        case_key = key_directory / (nonce.hex() + ".cases.key")
        create_encrypted_backup(source, directory / "cases.recase", case_key, directory / "cases-receipt.json")
        case_receipt_sha = file_digest(directory / "cases-receipt.json")
        header = {"format": PAIR_FORMAT, "created_at": utc_now(), "account_state_sha256": commitment,
                  "account_image_sha256": sha_bytes(image), "account_image_bytes": len(image),
                  "case_receipt_sha256": case_receipt_sha,
                  "account_count": len(rows), "nonce_hex": nonce.hex(),
                  "case_owner_bindings": [{"case": digest(r["id"]), "owner": digest(r["owner"])} for r in data["cases"]]}
        aad = ACCOUNT_MAGIC + canonical(header)
        ciphertext = AESGCM(key).encrypt(nonce, image, aad)
        # The account image and keys are retained even after a partial failure.
        key_path = key_directory / (nonce.hex() + ".accounts.key")
        write_bytes(key_path, key)
        write_bytes(directory / "accounts.recase", ciphertext)
        if account_snapshot(accounts)[2] != commitment or file_digest(journal) != journal_sha:
            raise RuntimeError("PAIR_INPUTS_CHANGED_PRESERVE_PARTIAL_OUTPUTS")
        manifest = {"format": PAIR_FORMAT, "status": "ENCRYPTED_PAIR_HELD_NOT_DEPLOYED", "header": header,
                    "account_ciphertext_sha256": sha_bytes(ciphertext), "case_receipt_sha256": case_receipt_sha,
                    "case_key_name": case_key.name, "account_key_name": key_path.name, "current_journal_sha256": journal_sha,
                    "ownership": ownership, "account_restore_implemented": False, "automatic_disposal_eligible": False,
                    "plaintext_backup_files_created": 0}
        manifest["manifest_sha256"] = digest(manifest)
        save_private(directory / "pair.json", manifest)
        return {"status": "PASS", "account_count": len(rows), "case_count": len(data["cases"]),
                "plaintext_backup_files_created": 0, "account_credentials_restored": False}


def load_pair(path):
    path = absolute_path(path)
    private_directory(path.parent)
    pair = json.loads(read_private(path, 1024 * 1024))
    if (not isinstance(pair, dict) or pair.get("format") != PAIR_FORMAT
            or pair.get("manifest_sha256") != digest({k: v for k, v in pair.items() if k != "manifest_sha256"})):
        raise ValueError("ACCOUNT_PAIR_MANIFEST_INTEGRITY_FAILURE")
    for name in ("case_key_name", "account_key_name"):
        value = pair.get(name)
        if not isinstance(value, str) or Path(value).name != value or value in {".", ".."} or "\\" in value:
            raise ValueError("ACCOUNT_PAIR_KEY_NAME_REFUSED")
    if (file_digest(path.parent / "cases-receipt.json") != pair.get("case_receipt_sha256")
            or pair.get("case_receipt_sha256") != pair.get("header", {}).get("case_receipt_sha256")):
        raise ValueError("ACCOUNT_PAIR_CASE_RECEIPT_CHANGED")
    return pair


def authenticated_account_image(manifest, key_directory):
    """Authenticate both pair bindings before exposing an account image in memory."""
    manifest, key_directory = absolute_path(manifest), private_directory(key_directory)
    separate_key_directory(manifest.parent, key_directory)
    pair = load_pair(manifest)
    key = read_private(key_directory / pair["account_key_name"], 32)
    encrypted = read_private(manifest.parent / "accounts.recase", MAX_ACCOUNT_BYTES + 16)
    if len(key) != 32 or sha_bytes(encrypted) != pair.get("account_ciphertext_sha256"):
        raise ValueError("ACCOUNT_PAIR_ENCRYPTED_INPUT_CHANGED")
    header = pair["header"]
    image = AESGCM(key).decrypt(bytes.fromhex(header["nonce_hex"]), encrypted, ACCOUNT_MAGIC + canonical(header))
    if len(image) != header["account_image_bytes"] or sha_bytes(image) != header["account_image_sha256"]:
        raise ValueError("ACCOUNT_PAIR_IMAGE_CHANGED")
    return pair, image, key


def verify_pair(manifest, key_directory, current_accounts, journal, scratch, report):
    require_operator()
    manifest, key_directory, current_accounts, journal = (absolute_path(p) for p in (manifest, key_directory, current_accounts, journal))
    scratch, report = private_new(scratch), private_new(report)
    case_report = private_new(scratch.parent / (scratch.name + ".case-proof.json"))
    if report == case_report or report == scratch or report.is_relative_to(scratch):
        raise ValueError("SEPARATE_PAIR_REPORT_REQUIRED")
    private_directory(scratch.parent)
    private_directory(report.parent)
    private_directory(key_directory)
    separate_key_directory(manifest.parent, key_directory)
    pair, image, account_key = authenticated_account_image(manifest, key_directory)
    manifest_sha = file_digest(manifest)
    journal_sha = sha_bytes(read_private(journal, 16 * 1024 * 1024))
    tombstones = {digest(r["payload"]["case_id"]) for r in read_ledger(journal) if r["payload"].get("action") == "delete_case"}
    header = pair["header"]
    with account_lock(current_accounts, exclusive=True):
        _, rows, current_commitment = account_snapshot(current_accounts)
        users = {digest(r["id"]) for r in rows}
        if any(r["case"] not in tombstones and r["owner"] not in users for r in header["case_owner_bindings"]):
            raise ValueError("CURRENT_ACCOUNT_OWNER_MISSING_NO_AUTOMATIC_ACCOUNT_RESTORE")
        # Restore only the case database and apply the latest independent journal.
        case_proof = verify_encrypted_backup(manifest.parent / "cases-receipt.json", key_directory / pair["case_key_name"],
                                             journal, scratch, case_report)
        _, data = read_snapshot(scratch / "restored.db")
        ownership = validate_owners(data, rows)
        if (account_snapshot(current_accounts)[2] != current_commitment or file_digest(journal) != journal_sha
                or file_digest(manifest) != manifest_sha
                or file_digest(manifest.parent / "accounts.recase") != pair["account_ciphertext_sha256"]
                or read_private(key_directory / pair["account_key_name"], 32) != account_key):
            raise RuntimeError("ACCOUNT_PAIR_INPUTS_CHANGED_NO_PASS_PROOF")
        result = {"format": "recase-account-pair-verification-v1", "status": "PASS", "checked_at": utc_now(),
                  "manifest_sha256": manifest_sha, "current_journal_sha256": journal_sha,
                  "current_account_state_sha256": current_commitment, "backup_account_state_sha256": header["account_state_sha256"],
                  "account_state_changed_since_backup": current_commitment != header["account_state_sha256"],
                  "checks": {"both_archives_authenticated": True, "current_account_database_preserved": True,
                             "historical_credentials_not_written_or_activated": True, "ownership": ownership,
                             "current_journal_applied": True, "restored_cases_held": True,
                             "case_sessions_revoked": case_proof["checks"]["sessions_revoked"]},
                  "browser_sessions": "Restart required; memory-only sessions are not in either backup",
                  "account_restore_implemented": False, "automatic_disposal_eligible": False,
                  "physical_or_crypto_erasure_verified": False, "scratch_contains_plaintext_cases": True}
        result["verification_sha256"] = digest(result)
        save_private(report, result)
        return result
