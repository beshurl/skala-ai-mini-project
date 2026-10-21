"""Single-use-key authenticated backups and copy-only restore checks; never erase.

No plaintext backup is written during creation. Restore scratch is plaintext and
must remain private. Key unavailability is not proof of cryptographic erasure.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import time
import uuid
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from recase.backup_receipts import new_path, preserved_content
from recase.ledger import digest, file_digest, read_ledger, utc_now
from recase.lifecycle import CORE_COLUMNS, case_identity, migrate_v1
from recase.operations_drill import save_private
from recase.retention import apply_deletions, deletion_events
from recase.retention_schedule import instant
from recase.store import Store

MAGIC = b"RECASE-AES256GCM-BACKUP-V1\n"
FORMAT = "recase-encrypted-backup-v1"
MAX_BYTES = 128 * 1024 * 1024
MAX_HEADER = 128 * 1024
CHECKS = {"authenticated_decryption", "integrity", "sessions_revoked", "pending_jobs_cleared",
          "surviving_content_preserved", "restored_retention_held", "encrypted_backup_unchanged",
          "receipt_unchanged", "key_unchanged", "current_journal_unchanged"}


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def absolute_path(path):
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Parent traversal paths refused")
    return path.absolute()


def private_new(path):
    return new_path(absolute_path(path))


def require_operator():
    if os.geteuid() == 0 or os.getuid() != os.geteuid():
        raise PermissionError("Run as the expected nonroot operator or service account")


def private_directory(path):
    path = absolute_path(path)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or any(p.is_symlink() for p in path.parents)):
        raise PermissionError("Existing operator-owned directory mode0700 without symlinks required")
    return path


def read_private(path, limit):
    path = absolute_path(path)
    if any(p.is_symlink() for p in path.parents):
        raise PermissionError("Symlink ancestors refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise PermissionError("Independent operator-owned regular file mode0600 required")
        if info.st_size > limit:
            raise ValueError("Private input size limit exceeded")
        value = stream.read(limit + 1)
        if len(value) > limit:
            raise ValueError("Private input size limit exceeded")
        return value


def write_bytes(path, value):
    private_directory(Path(path).parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def separate_key_directory(backup_dir, key_dir):
    # Compare inode ancestry too, because the Mac volume may ignore path case.
    identity = lambda p: (p.stat().st_dev, p.stat().st_ino)
    if (identity(backup_dir) in {identity(p) for p in (key_dir, *key_dir.parents)}
            or identity(key_dir) in {identity(p) for p in (backup_dir, *backup_dir.parents)}):
        raise ValueError("Keys must remain in a separate non-nested private directory")


def snapshot_bytes(source):
    """SQLite backup API -> bounded memory snapshot, including committed WAL pages."""
    source = absolute_path(source)
    # Validate metadata with no large source read. The SQLite connection is ro.
    info = source.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or any(p.is_symlink() for p in source.parents)):
        raise PermissionError("Independent private source database required")
    deadline = time.monotonic() + 15
    with Store(source, read_only=True).db() as source_db, closing(sqlite3.connect(":memory:")) as memory:
        page_size = source_db.execute("PRAGMA page_size").fetchone()[0]

        def progress(status, remaining, total):
            if total * page_size > MAX_BYTES or time.monotonic() > deadline:
                raise RuntimeError("Backup memory/time budget exceeded")

        source_db.backup(memory, pages=256, progress=progress, sleep=.01)
        memory.row_factory = sqlite3.Row
        version = memory.execute("PRAGMA user_version").fetchone()[0]
        if version not in {1, 2} or memory.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Healthy known RECASE schema1/schema2 snapshot required")
        for table, columns in CORE_COLUMNS.items():
            if {r[1] for r in memory.execute(f"PRAGMA table_info({table})")} != columns:
                raise ValueError("Known RECASE core column contract required")
        if version == 1:
            rows = [(r[0], "unclassified", 0) for r in memory.execute("SELECT id FROM cases ORDER BY id LIMIT 1001")]
        else:
            rows = list(memory.execute("SELECT c.id,l.data_class,l.hold FROM cases c LEFT JOIN case_lifecycle l ON l.case_id=c.id ORDER BY c.id LIMIT 1001"))
        if len(rows) > 1000:
            raise ValueError("Backup inventory limit1000 cases")
        data = memory.serialize()
        if len(data) > MAX_BYTES:
            raise ValueError("Backup memory limit128MiB")
        metadata = {"source_schema_version": version, "case_identities": [case_identity(r[0]) for r in rows],
                    "data_class": "synthetic_fixture" if rows and all(r[1] == "synthetic_fixture" for r in rows) else "unclassified",
                    "initial_hold": any(r[2] != 0 for r in rows)}
    after = source.lstat()
    if (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino):
        raise RuntimeError("Source database replaced during backup")
    return data, metadata


def create_encrypted_backup(source, target, key_path, receipt_path):
    require_operator()
    target, key_path, receipt_path = (private_new(p) for p in (target, key_path, receipt_path))
    backup_dir, key_dir = private_directory(target.parent), private_directory(key_path.parent)
    if receipt_path.parent != backup_dir or len({target, key_path, receipt_path}) != 3:
        raise ValueError("Backup/receipt together and key in a separate non-nested private directory required")
    separate_key_directory(backup_dir, key_dir)
    started = utc_now()
    plain, metadata = snapshot_bytes(source)
    created = utc_now()
    if instant(created) < instant(started):
        raise RuntimeError("Backup clock moved backwards")
    if shutil.disk_usage(backup_dir).free < len(plain) + MAX_HEADER + 16 * 1024 * 1024:
        raise RuntimeError("Insufficient free space for encrypted backup")
    # A new key is generated exactly once for this single immutable ciphertext.
    key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
    header = {"format": FORMAT, "backup_id": uuid.uuid4().hex, "algorithm": "AES-256-GCM",
              "nonce_hex": nonce.hex(), "started_at": started, "created_at": created,
              "plaintext_sha256": sha_bytes(plain), "plaintext_bytes": len(plain), **metadata}
    encoded = canonical(header)
    if len(encoded) > MAX_HEADER:
        raise ValueError("Bounded backup header required")
    aad = MAGIC + len(encoded).to_bytes(4, "big") + encoded
    encrypted = aad + AESGCM(key).encrypt(nonce, plain, aad)
    # Preserve any partial outputs on failure; never auto-remove keys/backups.
    write_bytes(key_path, key)
    write_bytes(target, encrypted)
    receipt = {"format": "encrypted-backup-receipt-v1", "backup_path": str(target),
               "encrypted_sha256": sha_bytes(encrypted), "header": header,
               "restore_verified": False, "physical_or_crypto_erasure_verified": False}
    receipt["receipt_sha256"] = digest(receipt)
    save_private(receipt_path, receipt)
    return {"status": "PASS", "worker_uid": os.getuid(), "worker_euid": os.geteuid(),
            "backup_id": header["backup_id"], "encrypted_sha256": receipt["encrypted_sha256"],
            "receipt_sha256": file_digest(receipt_path), "plaintext_backup_files_created": 0,
            "backup_or_key_erasure_executed": 0}


def read_receipt(path):
    path = absolute_path(path)
    private_directory(path.parent)
    receipt_bytes = read_private(path, 1024 * 1024)
    receipt = json.loads(receipt_bytes)
    if (not isinstance(receipt, dict) or receipt.get("format") != "encrypted-backup-receipt-v1"
            or digest({k: v for k, v in receipt.items() if k != "receipt_sha256"}) != receipt.get("receipt_sha256")):
        raise ValueError("Encrypted receipt integrity failure")
    if not Path(receipt["backup_path"]).is_absolute():
        raise ValueError("An absolute encrypted backup path is required")
    backup = absolute_path(receipt["backup_path"])
    if backup.parent != path.parent:
        raise ValueError("Receipt and encrypted backup must remain in the same private directory")
    encrypted = read_private(backup, MAX_BYTES + MAX_HEADER + len(MAGIC) + 20)
    if not encrypted.startswith(MAGIC) or sha_bytes(encrypted) != receipt.get("encrypted_sha256"):
        raise ValueError("Encrypted backup bytes changed")
    length = int.from_bytes(encrypted[len(MAGIC):len(MAGIC) + 4], "big")
    offset = len(MAGIC) + 4 + length
    if not 1 <= length <= MAX_HEADER or offset + 16 > len(encrypted):
        raise ValueError("Invalid encrypted header size")
    encoded = encrypted[len(MAGIC) + 4:offset]
    header = json.loads(encoded)
    if not isinstance(header, dict) or canonical(header) != encoded or header != receipt.get("header"):
        raise ValueError("Encrypted header/receipt mismatch")
    identities = header.get("case_identities")
    hex_value = lambda v, n: isinstance(v, str) and len(v) == n and all(c in "0123456789abcdef" for c in v)
    if (header.get("format") != FORMAT or header.get("algorithm") != "AES-256-GCM"
            or not hex_value(header.get("backup_id"), 32) or not hex_value(header.get("nonce_hex"), 24)
            or not hex_value(header.get("plaintext_sha256"), 64)
            or type(header.get("plaintext_bytes")) is not int or not 1 <= header["plaintext_bytes"] <= MAX_BYTES
            or type(header.get("source_schema_version")) is not int or header["source_schema_version"] not in {1, 2}
            or header.get("data_class") not in {"synthetic_fixture", "unclassified"}
            or type(header.get("initial_hold")) is not bool or not isinstance(identities, list)
            or len(identities) > 1000 or any(not hex_value(i, 64) for i in identities)
            or len(set(identities)) != len(identities)
            or instant(header["created_at"]) < instant(header["started_at"])):
        raise ValueError("Invalid authenticated backup metadata")
    return receipt, encrypted[:offset], encrypted[offset:], sha_bytes(receipt_bytes)


def verify_encrypted_backup(receipt_path, key_path, journal, scratch, report_path):
    require_operator()
    report_path, scratch = private_new(report_path), private_new(scratch)
    private_directory(scratch.parent)
    private_directory(report_path.parent)
    if report_path == scratch or report_path.is_relative_to(scratch):
        raise ValueError("Separate scratch and report destinations required")
    key_path = absolute_path(key_path)
    separate_key_directory(private_directory(Path(receipt_path).absolute().parent), private_directory(key_path.parent))
    journal = absolute_path(journal)
    journal_bytes = read_private(journal, 16 * 1024 * 1024)
    read_ledger(journal)
    journal_sha = sha_bytes(journal_bytes)
    receipt, aad, ciphertext, receipt_sha = read_receipt(receipt_path)
    key = read_private(key_path, 32)
    if len(key) != 32:
        raise ValueError("A private256-bit backup key is required")
    header = receipt["header"]
    # Authentication is complete before any plaintext destination is created.
    plain = AESGCM(key).decrypt(bytes.fromhex(header["nonce_hex"]), ciphertext, aad)
    if len(plain) != header["plaintext_bytes"] or sha_bytes(plain) != header["plaintext_sha256"]:
        raise ValueError("Authenticated plaintext size/hash mismatch")
    if shutil.disk_usage(scratch.parent).free < 4 * len(plain) + 16 * 1024 * 1024:
        raise RuntimeError("Insufficient free space for private restore scratch")
    exclusions = {e["case_id"] for e in deletion_events(journal)}
    scratch.mkdir(mode=0o700)
    restored = scratch / "restored.db"
    # SQLite handles the serialized WAL-format snapshot as a new database file;
    # in-memory deserialize cannot reopen a WAL image. Do not patch its header.
    write_bytes(restored, plain)
    with Store(restored, read_only=True).db() as db:
        if db.execute("PRAGMA user_version").fetchone()[0] != header["source_schema_version"]:
            raise ValueError("Snapshot schema differs from authenticated metadata")
        expected = preserved_content(db, exclusions)
    migration = migrate_v1(restored, scratch / "schema1-rollback.db") if header["source_schema_version"] == 1 else None
    replay = apply_deletions(restored, journal)
    recovered = Store(restored).recover()
    with Store(restored, read_only=True).db() as db:
        checks = {"authenticated_decryption": True,
                  "integrity": db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                  "sessions_revoked": db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0,
                  "pending_jobs_cleared": db.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[0] == 0,
                  "surviving_content_preserved": expected == preserved_content(db, set()),
                  "restored_retention_held": db.execute("SELECT count(*) FROM case_lifecycle WHERE hold!=1").fetchone()[0] == 0}
    checks.update(encrypted_backup_unchanged=file_digest(receipt["backup_path"]) == receipt["encrypted_sha256"],
                  receipt_unchanged=file_digest(receipt_path) == receipt_sha,
                  key_unchanged=sha_bytes(read_private(key_path, 32)) == sha_bytes(key),
                  current_journal_unchanged=file_digest(journal) == journal_sha)
    if set(checks) != CHECKS or not all(checks.values()):
        raise RuntimeError("Encrypted restore verification failed; preserve scratch for diagnosis")
    report = {"format": "encrypted-backup-verification-v1", "status": "PASS", "checked_at": utc_now(),
              "worker_uid": os.getuid(), "worker_euid": os.geteuid(),
              "receipt_file_sha256": receipt_sha, "encrypted_sha256": receipt["encrypted_sha256"],
              "key_sha256": sha_bytes(key), "journal_sha256": journal_sha, "checks": checks,
              "scratch_schema_migration": migration, "replay": replay, "jobs_marked_server_restarted": recovered,
              "backup_or_key_erasure_executed": 0, "physical_or_crypto_erasure_verified": False,
              "scratch_contains_plaintext": True,
              "trust_scope": "Current explicitly supplied independent journal and local operator proof; not a malicious same-UID boundary"}
    report["verification_sha256"] = digest(report)
    save_private(report_path, report)
    return report


def encrypted_inventory(receipt_paths, verification_paths, key_paths, journal, case_inventory):
    require_operator()
    if any(len(paths) > 100 for paths in (receipt_paths, verification_paths, key_paths)):
        raise ValueError("Encrypted inventory limit100 backups/keys/proofs")
    journal_sha = sha_bytes(read_private(journal, 16 * 1024 * 1024))
    read_ledger(journal)
    verifications = {}
    for path in verification_paths:
        proof = json.loads(read_private(path, 1024 * 1024))
        if not isinstance(proof, dict) or proof.get("verification_sha256") != digest({k: v for k, v in proof.items() if k != "verification_sha256"}):
            raise ValueError("Encrypted verification receipt integrity failure")
        verifications.setdefault(proof.get("receipt_file_sha256"), []).append(proof)
    available_keys = set()
    key_directories = set()
    for path in key_paths:
        private_directory(absolute_path(path).parent)
        try:
            key = read_private(path, 32)
        except FileNotFoundError:
            continue  # Missing keys make restore unverified, never proof of erasure.
        if len(key) != 32:
            raise ValueError("Private256-bit keys required")
        available_keys.add(sha_bytes(key))
        key_directories.add(absolute_path(path).parent)
    holds = {row["identity_sha256"] for row in case_inventory["cases"] if row["hold"]}
    rows, seen = [], set()
    for path in receipt_paths:
        receipt, _, _, receipt_sha = read_receipt(path)
        for key_dir in key_directories:
            separate_key_directory(absolute_path(receipt["backup_path"]).parent, key_dir)
        header = receipt["header"]
        identity = digest(["encrypted_backup", header["backup_id"]])
        if identity in seen:
            raise ValueError("Duplicate encrypted backup receipt")
        seen.add(identity)
        verified = any(p.get("format") == "encrypted-backup-verification-v1" and p.get("status") == "PASS"
                       and p.get("encrypted_sha256") == receipt["encrypted_sha256"] and p.get("journal_sha256") == journal_sha
                       and p.get("key_sha256") in available_keys and set(p.get("checks", {})) == CHECKS
                       and all(v is True for v in p["checks"].values())
                       for p in verifications.get(receipt_sha, []))
        rows.append({"identity_sha256": identity, "created_at": header["created_at"], "data_class": header["data_class"],
                     "hold": header["initial_hold"] or bool(holds & set(header["case_identities"])),
                     "restore_verified": verified, "encrypted": True,
                     "verification_scope": "Immutable authenticated archive; current supplied journal and available verified key; preview only",
                     "physical_or_crypto_erasure_verified": False})
    if file_digest(journal) != journal_sha:
        raise RuntimeError("Journal changed during encrypted inventory export")
    return rows
