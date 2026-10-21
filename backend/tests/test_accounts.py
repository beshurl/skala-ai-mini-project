"""Real local password hashing/session/ownership tests with disposable fixture accounts."""
import hashlib
import json
import sqlite3

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from recase.accounts import Accounts, COOKIE, password_hash, password_matches
from recase.api import create_app
from recase.testing import FixtureModel
from tests.account_helpers import PASSWORD, signup, enter_demo


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "cases.db", FixtureModel(), testing=True)) as client:
        yield client


def test_password_storage_salt_and_private_files(tmp_path):
    a, b = password_hash(PASSWORD), password_hash(PASSWORD)
    assert a != b and password_matches(PASSWORD, a) and not password_matches("incorrect", a)
    accounts = Accounts(tmp_path / "accounts.db")
    user = accounts.create("User@Example.test", PASSWORD, "검토자")
    assert user["email"] == "user@example.test" and user["role"] == "user"
    with accounts.db() as db:
        raw = dict(db.execute("SELECT * FROM accounts").fetchone())
    assert PASSWORD not in json.dumps(raw) and raw["password_hash"].startswith("scrypt$32768$8$3$")
    assert accounts.path.stat().st_mode & 0o777 == 0o600
    accounts.path.chmod(0o644)
    with pytest.raises(PermissionError):
        Accounts(accounts.path)


def test_registration_login_logout_csrf_and_stable_owner(client):
    assert client.get("/").status_code in (200, 503)  # Public shell does not depend on an account.
    assert client.get("/api/cases").status_code == 401
    profile = signup(client, "user@example.test")
    cookie = client.cookies.get(COOKIE)
    assert COOKIE in str(client.cookies)
    assert client.post("/api/demo").status_code == 403
    assert enter_demo(client).status_code == 201
    cases = client.get("/api/cases").json()
    assert len(cases) == 2 and all(c["id"] for c in cases)
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers={"x-recase-csrf": profile["csrf"]}).status_code == 200
    assert client.get("/api/cases").status_code == 401
    assert client.post("/api/auth/login", json={"email":profile["email"],"password":"wrong"}).status_code == 401
    response = client.post("/api/auth/login", json={"email":profile["email"].upper(),"password":PASSWORD})
    assert response.status_code == 200 and response.json()["user_id"] == profile["user_id"]
    assert client.cookies.get(COOKIE) != cookie
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    assert {c["id"] for c in client.get("/api/cases").json()} == {c["id"] for c in cases}
    assert enter_demo(client).status_code == 201 and len(client.get("/api/cases").json()) == 2


def test_other_account_cannot_read_write_or_stream_case(client):
    first = signup(client)
    enter_demo(client)
    case = client.get("/api/cases").json()[0]
    second = signup(client)
    assert second["user_id"] != first["user_id"]
    assert client.get(f'/api/cases/{case["id"]}').status_code == 404
    assert client.post(f'/api/cases/{case["id"]}/release', json={"evidence_version":1}, headers={"x-recase-csrf":second["csrf"]}).status_code == 404
    assert client.get("/api/cases").json() == []


def test_roles_are_server_owned_and_legacy_login_is_removed(client):
    body = {"email":"forged@example.test","password":PASSWORD,"name":"test","role":"admin"}
    denied = client.post("/api/auth/register", json=body)
    assert denied.status_code == 422 and PASSWORD not in denied.text
    profile = signup(client)
    assert profile["role"] == "user" and client.get("/api/admin/summary").status_code == 403
    assert client.post("/api/admin/login", json={"access_key":"anything"}).status_code == 404
    assert client.post("/api/local-login", data={"access_key":"anything"}).status_code == 404


def test_auth_origin_validation_rate_and_no_password_in_errors(client):
    body = {"email":"valid@example.test","password":PASSWORD,"name":"tester"}
    assert client.post("/api/auth/register", json=body, headers={"origin":"https://evil.example"}).status_code == 403
    assert client.post("/api/auth/login", json=body, headers={"sec-fetch-site":"cross-site"}).status_code == 403
    invalid = client.post("/api/auth/register", json={**body,"password":PASSWORD * 30})
    assert invalid.status_code == 422 and PASSWORD not in invalid.text and "input" not in invalid.text
    assert client.post("/api/auth/register", json={**body,"password":"short"}).json()["detail"] == "PASSWORD_LENGTH"
    assert client.post("/api/auth/register", json={**body,"email":"not-an-email"}).json()["detail"] == "INVALID_EMAIL"
    assert client.post("/api/auth/login", content=json.dumps(body),headers={"content-type":"text/plain"}).status_code in (415, 422)
    for _ in range(8):
        assert client.post("/api/auth/login",json={"email":"unknown@example.test","password":PASSWORD}).status_code == 401
    limited=client.post("/api/auth/login",json={"email":"unknown@example.test","password":PASSWORD})
    assert limited.status_code == 429 and limited.headers["retry-after"] == "60"


def test_restart_reset_disable_and_role_change_revoke_sessions(tmp_path):
    path=tmp_path / "accounts.db"
    accounts=Accounts(path)
    user=accounts.create("user@example.test", PASSWORD, "UNIT_TEST")
    cookie, _=accounts.new_session(user)
    assert hashlib.sha256(cookie.encode()).hexdigest() in accounts._sessions
    assert cookie not in str(accounts._sessions)
    restarted=Accounts(path)
    with pytest.raises(HTTPException):
        restarted.session(cookie)
    restarted.reset_password(user["email"], PASSWORD + "-changed")
    with pytest.raises(HTTPException):
        accounts.session(cookie)
    cookie, _=accounts.login(user["email"],PASSWORD + "-changed","test-ip")
    with accounts.db() as db:db.execute("UPDATE accounts SET role='admin' WHERE id=?",(user["id"],))
    with pytest.raises(HTTPException):accounts.session(cookie)
    cookie, _=accounts.login(user["email"],PASSWORD + "-changed","test-ip")
    with accounts.db() as db:db.execute("UPDATE accounts SET enabled=0 WHERE id=?",(user["id"],))
    with pytest.raises(HTTPException):accounts.session(cookie)


def test_missing_journal_and_legacy_env_refused_without_security_downgrade(tmp_path, monkeypatch):
    monkeypatch.setenv("RECASE_AUTH_FILE", str(tmp_path / "old.json"))
    with pytest.raises(RuntimeError, match="ACCESS_KEY_AUTH_REMOVED"):
        create_app(tmp_path / "db", FixtureModel(), testing=True)
    monkeypatch.delenv("RECASE_AUTH_FILE")
    with pytest.raises(RuntimeError, match="independent"):
        with TestClient(create_app(tmp_path / "new.db", FixtureModel(), testing=True, deletions_file=tmp_path / "missing.jsonl")):
            pass


def test_wrong_database_schema_and_noninteractive_admin_creation_are_refused(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    path=tmp_path / "wrong.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated(value TEXT)")
        db.execute("PRAGMA user_version=1")
    path.chmod(0o600)
    before=path.read_bytes()
    with pytest.raises(ValueError, match="schema differs"):
        Accounts(path)
    assert path.read_bytes() == before
    destination=tmp_path / "must-not-be-created.db"
    command=[sys.executable,str(Path(__file__).parents[1]/"scripts/accounts.py"),"create-admin","--email","operator@example.test","--db",str(destination)]
    result=subprocess.run(command,input=PASSWORD,text=True,capture_output=True)
    assert result.returncode != 0 and not destination.exists() and PASSWORD not in result.stdout+result.stderr
