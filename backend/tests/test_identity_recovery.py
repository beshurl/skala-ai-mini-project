"""Fresh synthetic lost-account recovery; no real identity attestation."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from recase.account_backups import create_pair, verify_pair
from recase.accounts import Accounts, COOKIE
from recase.account_state import account_snapshot
from recase.api import create_app
from recase.identity_recovery import QUARANTINE_VERSION, activate_user, seal_recovery, stage_identities
from recase.ledger import append_record, digest, file_digest, read_ledger
from recase.store import Store
from recase.testing import FixtureModel
from tests.account_helpers import PASSWORD


def fixture(tmp_path, wal=False):
    a = Accounts(tmp_path / "source-accounts.db")
    owner = a.create("owner@example.test", PASSWORD, "SYNTHETIC_OWNER")
    admin = a.create("old-operator@example.test", PASSWORD, "SYNTHETIC_ADMIN", role="admin")
    if wal:
        with a.db() as db:
            db.execute("PRAGMA journal_mode=WAL")
    store = Store(tmp_path / "cases.db")
    store.seed_demo(owner["id"])
    case = store.cases(owner["id"])[0]
    job = store.create_job(owner["id"], case["id"], 1, {"backend":"synthetic"})
    store.set_status(owner["id"], job["id"], "COMPLETED", result={"fixture":"KEEP_RESULT"})
    journal = tmp_path / "deletions.jsonl"
    append_record(journal, {"action":"initialize", "scope":"SYNTHETIC_RECOVERY_ONLY"})
    keys = tmp_path / "keys"
    keys.mkdir(mode=0o700)
    pair = tmp_path / "pair"
    create_pair(store.path, a.path, journal, pair, keys)
    target, proof = tmp_path / "staged-accounts.db", tmp_path / "recovery.json"
    return a, owner, admin, store, case, job, journal, keys, pair, target, proof


@pytest.mark.parametrize("wal", [False, True])
def test_stage_writes_only_disabled_user_identities_and_never_old_passwords(tmp_path, wal):
    a, owner, admin, store, _, _, _, keys, pair, target, proof = fixture(tmp_path, wal)
    _, originals, _ = account_snapshot(a.path)
    before = {p:file_digest(p) for p in [a.path,store.path,pair/"pair.json"]}
    result = stage_identities(pair/"pair.json", keys, target, proof)
    assert result["status"] == "QUARANTINED_NOT_DEPLOYABLE"
    _, staged, _ = account_snapshot(target, (QUARANTINE_VERSION,))
    assert {r["id"] for r in staged} == {owner["id"],admin["id"]}
    assert all(not r["enabled"] and r["role"]=="user" for r in staged)
    raw = target.read_bytes()
    assert all(r["password_hash"].encode() not in raw for r in originals)
    assert PASSWORD.encode() not in raw
    with pytest.raises(ValueError,match="Unrecognized"):
        Accounts(target)
    assert all(file_digest(p)==sha for p,sha in before.items())
    assert owner["email"] not in proof.read_text() and owner["id"] not in proof.read_text()


def test_review_activate_seal_restore_keeps_owned_cases_and_blocks_old_sessions_and_admin(tmp_path):
    a, owner, admin, _, case, job, journal, keys, pair, target, proof = fixture(tmp_path)
    old_cookie, _ = a.login(owner["email"],PASSWORD,"fixture")
    stage_identities(pair/"pair.json",keys,target,proof)
    activate_user(target,proof,owner["email"],owner["id"],PASSWORD+"-new","UNIT_TEST_FIXTURE simulated identity check")
    with pytest.raises(ValueError):
        Accounts(target)  # Individual activation does not remove quarantine.
    seal = seal_recovery(target,proof,tmp_path/"seal.json",{admin["id"]})
    assert seal["active_user_count"]==1 and seal["held_user_count"]==1 and seal["admin_count"]==0
    current = Accounts(target)
    with pytest.raises(HTTPException):
        current.login(owner["email"],PASSWORD,"fixture")
    with pytest.raises(HTTPException):
        current.login(admin["email"],PASSWORD,"fixture")
    assert current.login(owner["email"],PASSWORD+"-new","fixture")[1]["role"]=="user"
    verify_pair(pair/"pair.json",keys,target,journal,tmp_path/"restored",tmp_path/"restore-proof.json")
    with TestClient(create_app(tmp_path/"restored/restored.db",FixtureModel(),testing=True,accounts_path=target,deletions_file=journal)) as client:
        client.cookies.set(COOKIE,old_cookie)
        assert client.get('/api/cases').status_code==401
        response=client.post('/api/auth/login',json={"email":owner["email"],"password":PASSWORD+"-new"})
        assert response.status_code==200
        assert client.get('/api/jobs/'+job['id']).json()['result']['fixture']=='KEEP_RESULT'
        assert client.get('/api/cases/'+case['id']).status_code==200
        assert client.get('/api/admin/summary').status_code==403
    logs=read_ledger(proof.with_name(proof.stem+'.actions.jsonl'))
    assert [r['payload']['action'] for r in logs]==['recovery_staged','activation_intent','activation_completed','seal_intent','recovery_sealed']
    assert PASSWORD not in json.dumps(logs)


def test_wrong_identity_password_and_unacknowledged_held_accounts_make_no_activation(tmp_path):
    _, owner, admin, _, _, _, _, keys, pair, target, proof = fixture(tmp_path)
    stage_identities(pair/'pair.json',keys,target,proof)
    before=account_snapshot(target,(QUARANTINE_VERSION,))[2]
    with pytest.raises(ValueError,match='EXACT_DISABLED'):
        activate_user(target,proof,owner['email'],admin['id'],PASSWORD+'-new','UNIT_TEST_FIXTURE')
    with pytest.raises(HTTPException):
        activate_user(target,proof,owner['email'],owner['id'],'short','UNIT_TEST_FIXTURE')
    with pytest.raises(ValueError,match='EXACT_HELD'):
        seal_recovery(target,proof,tmp_path/'must-not-exist.json',set())
    assert account_snapshot(target,(QUARANTINE_VERSION,))[2]==before
    assert not (tmp_path/'must-not-exist.json').exists()


def test_pending_intent_or_external_state_change_requires_operator_audit(tmp_path):
    _, owner, _, _, _, _, _, keys, pair, target, proof = fixture(tmp_path)
    stage_identities(pair/'pair.json',keys,target,proof)
    ledger=proof.with_name(proof.stem+'.actions.jsonl')
    append_record(ledger,{"action":"activation_intent","scope":"SYNTHETIC_CRASH_SIMULATION"})
    with pytest.raises(RuntimeError,match='OPERATOR_AUDIT'):
        activate_user(target,proof,owner['email'],owner['id'],PASSWORD+'-new','UNIT_TEST_FIXTURE')
    assert all(not r['enabled'] for r in account_snapshot(target,(QUARANTINE_VERSION,))[1])


def test_existing_destination_or_wrong_key_never_overwrites_or_writes_old_image(tmp_path):
    _, _, _, _, _, _, _, keys, pair, target, proof = fixture(tmp_path)
    target.write_bytes(b'PRESERVE_CURRENT_DATABASE');target.chmod(0o600)
    with pytest.raises(FileExistsError):
        stage_identities(pair/'pair.json',keys,target,proof)
    assert target.read_bytes()==b'PRESERVE_CURRENT_DATABASE'
    key=keys/json.loads((pair/'pair.json').read_text())['account_key_name']
    key.rename(key.with_suffix('.unavailable'))  # Retained test key; no erasure.
    with pytest.raises(FileNotFoundError):
        stage_identities(pair/'pair.json',keys,tmp_path/'new.db',proof)
    assert not (tmp_path/'new.db').exists() and not proof.exists()


def test_existing_account_handle_refuses_quarantine_schema_and_replaced_file(tmp_path):
    a=Accounts(tmp_path/'accounts.db')
    user=a.create('owner@example.test',PASSWORD,'SYNTHETIC_OWNER')
    with a.db() as db:
        db.execute('PRAGMA user_version='+str(QUARANTINE_VERSION))
    with pytest.raises(ValueError,match='schema no longer usable'):
        a.get(user['id'])
    a.path.rename(tmp_path/'original.retained.db')
    other=Accounts(a.path)
    with pytest.raises(RuntimeError,match='REPLACED_RESTART'):
        a.get(user['id'])


@pytest.mark.parametrize("action",['activate-user','seal'])
def test_noninteractive_confirmation_is_refused_before_read_or_write(tmp_path, action):
    script=Path(__file__).parents[1]/'scripts/recover_accounts.py'
    args=[sys.executable,str(script),action,'--db',str(tmp_path/'missing.db'),'--proof',str(tmp_path/'missing.json')]
    args+=['--email','fixture@example.test','--user-id','USER-'+'a'*32] if action=='activate-user' else ['--out',str(tmp_path/'out.json')]
    result=subprocess.run(args,input=PASSWORD,text=True,capture_output=True)
    assert result.returncode==2 and 'local terminal' in result.stderr and PASSWORD not in result.stdout+result.stderr
    assert list(tmp_path.iterdir())==[]
