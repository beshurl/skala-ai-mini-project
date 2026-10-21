"""Account-aware release/backup regression tests on disposable synthetic data."""
import json
import os
import time
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient

from recase.accounts import Accounts, COOKIE
from recase.account_state import account_lock, account_snapshot
from recase.account_backups import create_pair, verify_pair
from recase.api import create_app
from recase.ledger import append_record, digest, file_digest
from recase.release_validation import check_transition
from recase.retention import apply_deletions
from recase.store import Store
from recase.testing import FixtureModel
from tests.account_helpers import PASSWORD


def setup(tmp_path):
    accounts = Accounts(tmp_path / "accounts.db")
    user = accounts.create("owner@example.test", PASSWORD, "SYNTHETIC_OWNER")
    admin = accounts.create("operator@example.test", PASSWORD, "SYNTHETIC_ADMIN", role="admin")
    store = Store(tmp_path / "cases.db")
    store.seed_demo(user["id"])
    cases = store.cases(user["id"])
    job = store.create_job(user["id"], cases[0]["id"], 1, {"backend": "fixture"})
    store.set_status(user["id"], job["id"], "COMPLETED", result={"fixture": "preserve historical result"})
    journal = tmp_path / "deletions.jsonl"
    append_record(journal, {"action": "initialize", "scope": "SYNTHETIC_ACCOUNT_INTEGRATION"})
    keys = tmp_path / "keys"
    keys.mkdir(mode=0o700)
    return accounts, user, admin, store, cases, job, journal, keys


def backup(tmp_path, parts):
    a, _, _, s, _, _, j, keys = parts
    directory = tmp_path / "pair"
    assert create_pair(s.path, a.path, j, directory, keys)["status"] == "PASS"
    return directory / "pair.json"


def verify(tmp_path, parts, pair, **kwargs):
    a, _, _, _, _, _, j, keys = parts
    return verify_pair(pair, keys, kwargs.get("accounts", a.path), j, tmp_path / "restored", tmp_path / "proof.json")


def release(tmp_path):
    root = tmp_path / "release"
    files = []
    for name in ("api", "store", "lifecycle", "model", "worker", "mcp_client", "accounts", "auth_api", "account_state"):
        files.append("backend/recase/" + name + ".py")
    files += ["backend/requirements-lock-macos-arm64.txt", "frontend/dist/index.html"]
    entries = []
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text("SCHEMA_VERSION = 2\n" if name.endswith("lifecycle.py") else "# synthetic contract fixture\n")
        path.chmod(0o600)
        entries.append({"path": name, "bytes": path.stat().st_size, "sha256": file_digest(path)})
    manifest = tmp_path / "release.json"
    manifest.write_text(json.dumps({"format": "recase-local-release-v2", "writable_schema_version": 2,
                                   "auth_contract": "account-password-v1", "file_count": len(entries), "files": entries}))
    manifest.chmod(0o600)
    return manifest, root


def test_pair_restore_keeps_current_password_role_disable_and_journal(tmp_path):
    parts = setup(tmp_path)
    a, user, admin, s, cases, _, j, _ = parts
    pair = backup(tmp_path, parts)
    a.reset_password(user["email"], PASSWORD + "-current")
    with a.db() as db:
        db.execute("UPDATE accounts SET role='user',credential_version=credential_version+1 WHERE id=?", (admin["id"],))
    append_record(j, {"action": "delete_case", "owner": user["id"], "case_id": cases[1]["id"]})
    before = account_snapshot(a.path)[2]
    proof = verify(tmp_path, parts, pair)
    assert proof["account_state_changed_since_backup"] and proof["checks"]["historical_credentials_not_written_or_activated"]
    assert account_snapshot(a.path)[2] == before
    restored = Store(tmp_path / "restored/restored.db", read_only=True)
    assert len(restored.cases(user["id"])) == 1 and restored.lifecycle(user["id"], cases[0]["id"])["hold"]
    assert a.get(admin["id"])["role"] == "user"
    reports = pair.read_text() + (tmp_path / "proof.json").read_text()
    assert PASSWORD not in reports and "scrypt$" not in reports and user["email"] not in reports
    assert user["id"] not in reports
    assert not any(p.name.endswith(".db") for p in pair.parent.iterdir())


def test_restored_api_restarts_sessions_and_preserves_ownership_results_and_current_roles(tmp_path):
    parts = setup(tmp_path)
    a, user, admin, s, cases, job, j, _ = parts
    old_cookie, _ = a.login(user["email"], PASSWORD, "fixture")
    pair = backup(tmp_path, parts)
    a.reset_password(user["email"], PASSWORD + "-current")
    with a.db() as db:
        db.execute("UPDATE accounts SET enabled=0,credential_version=credential_version+1 WHERE id=?", (admin["id"],))
    verify(tmp_path, parts, pair)
    app = create_app(tmp_path / "restored/restored.db", FixtureModel(), testing=True, accounts_path=a.path, deletions_file=j)
    with TestClient(app) as client:
        client.cookies.set(COOKIE, old_cookie)
        assert client.get("/api/cases").status_code == 401
        assert client.post("/api/auth/login", json={"email":user["email"],"password":PASSWORD}).status_code == 401
        assert client.post("/api/auth/login", json={"email":admin["email"],"password":PASSWORD}).status_code == 401
        profile = client.post("/api/auth/login", json={"email":user["email"],"password":PASSWORD + "-current"}).json()
        assert {c["id"] for c in client.get("/api/cases").json()} == {c["id"] for c in cases}
        assert client.get("/api/jobs/" + job["id"]).json()["result"]["fixture"] == "preserve historical result"
        assert client.get("/api/admin/summary").status_code == 403
        stranger = app.state.accounts.create("stranger@example.test", PASSWORD, "SYNTHETIC_STRANGER")
        assert client.post("/api/auth/login", json={"email":stranger["email"],"password":PASSWORD}).status_code == 200
        assert client.get("/api/cases/" + cases[0]["id"]).status_code == 404
        assert client.get("/api/jobs/" + job["id"]).status_code == 404


@pytest.mark.parametrize("problem", ["missing-current", "missing-key", "tamper", "wrong-key"])
def test_pair_never_restores_historical_credentials_or_writes_plaintext_before_prechecks(tmp_path, problem):
    parts = setup(tmp_path)
    pair = backup(tmp_path, parts)
    a, user, _, _, _, _, _, keys = parts
    if problem == "missing-current":
        with a.db() as db:
            db.execute("DELETE FROM accounts WHERE id=?", (user["id"],))
    elif problem == "tamper":
        archive = pair.parent / "accounts.recase"
        raw = archive.read_bytes()
        archive.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        obj = json.loads(pair.read_text())
        obj["account_ciphertext_sha256"] = file_digest(archive)
        obj["manifest_sha256"] = digest({k:v for k,v in obj.items() if k != "manifest_sha256"})
        pair.write_text(json.dumps(obj))
    else:
        key = keys / json.loads(pair.read_text())["account_key_name"]
        if problem == "missing-key":
            key.rename(key.with_suffix(".unavailable"))  # Test key retained, no erasure.
        else:
            key.write_bytes(os.urandom(32))
    with pytest.raises((ValueError, FileNotFoundError, InvalidTag)):
        verify(tmp_path, parts, pair)
    assert not (tmp_path / "restored").exists() and not (tmp_path / "proof.json").exists()


def test_account_maintenance_excludes_password_mutations_and_pair_on_active_service(tmp_path):
    parts = setup(tmp_path)
    a, _, _, s, _, _, _, _ = parts
    with account_lock(a.path, exclusive=True):
        with pytest.raises(RuntimeError, match="MAINTENANCE_BUSY"):
            a.reset_password("owner@example.test", PASSWORD + "-new")
    import fcntl
    with s.path.with_name(s.path.name + ".server.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        with pytest.raises(RuntimeError, match="SERVER_RUNNING"):
            backup(tmp_path, parts)
    assert not (tmp_path / "pair").exists()


def test_pair_authentication_binds_case_receipt_even_if_local_hashes_are_recomputed(tmp_path):
    parts = setup(tmp_path)
    pair = backup(tmp_path, parts)
    # Substitute a locally changed receipt and recompute every unkeyed binding.
    # The account archive must still reject the changed pair as an AEAD failure.
    receipt = pair.parent / "cases-receipt.json"
    obj = json.loads(receipt.read_text())
    obj["restore_verified"] = True
    obj["receipt_sha256"] = digest({k:v for k,v in obj.items() if k != "receipt_sha256"})
    receipt.write_text(json.dumps(obj))
    manifest = json.loads(pair.read_text())
    manifest["case_receipt_sha256"] = file_digest(receipt)
    manifest["header"]["case_receipt_sha256"] = manifest["case_receipt_sha256"]
    manifest["manifest_sha256"] = digest({k:v for k,v in manifest.items() if k != "manifest_sha256"})
    pair.write_text(json.dumps(manifest))
    with pytest.raises(InvalidTag):
        verify(tmp_path, parts, pair)
    assert not (tmp_path / "restored").exists() and not (tmp_path / "proof.json").exists()


def test_account_aware_transition_requires_same_current_accounts_and_rejects_legacy_code(tmp_path):
    parts = setup(tmp_path)
    a, _, _, s, _, _, j, _ = parts
    manifest, root = release(tmp_path)
    target = s.backup(tmp_path / "target.db")
    apply_deletions(target, j)
    args = [s.path, target, j, manifest, root]
    with pytest.raises(ValueError, match="CURRENT_ACCOUNT_DATABASE"):
        check_transition(*args, tmp_path / "missing.json")
    other = Accounts(tmp_path / "old-accounts.db")
    with pytest.raises(ValueError, match="ROLLBACK_REFUSED"):
        check_transition(*args, tmp_path / "old.json", a.path, other.path)
    obj = json.loads(manifest.read_text())
    del obj["auth_contract"]
    manifest.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="ACCOUNT_RELEASE_CONTRACT"):
        check_transition(*args, tmp_path / "legacy.json", a.path, a.path)
    obj["auth_contract"] = "account-password-v1"
    manifest.write_text(json.dumps(obj))
    proof = check_transition(*args, tmp_path / "pass.json", a.path, a.path)
    assert proof["account_checks"]["same_current_accounts"]


def test_unmapped_legacy_owner_and_job_owner_mismatch_are_blocked(tmp_path):
    parts = setup(tmp_path)
    a, _, _, s, _, job, _, _ = parts
    with s.db() as db:
        db.execute("UPDATE jobs SET owner='wrong' WHERE id=?", (job["id"],))
    with pytest.raises(ValueError, match="JOB_ACCOUNT_OWNER"):
        backup(tmp_path, parts)
    with s.db() as db:
        db.execute("UPDATE cases SET owner='legacy-session-owner'")
    with pytest.raises(ValueError, match="UNMAPPED_LEGACY"):
        backup(tmp_path, parts)


def test_accounts_link_and_unknown_schema_are_refused(tmp_path):
    a = Accounts(tmp_path / "accounts.db")
    os.link(a.path, tmp_path / "linked.db")
    with pytest.raises(PermissionError):
        account_snapshot(a.path)
    with pytest.raises(PermissionError):
        Accounts(a.path)
