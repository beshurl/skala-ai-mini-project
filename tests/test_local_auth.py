import json

import pytest
from fastapi.testclient import TestClient

from recase.api import create_app
from recase.local_auth import LocalAuth, provision
from recase.testing import FixtureModel


def test_local_key_authentication_and_revocation_preserve_case_csrf_scope(tmp_path):
    credential = provision(tmp_path / "credential", "test-operator")
    key = (tmp_path / "credential/key.txt").read_text().strip()
    with TestClient(create_app(tmp_path / "db.sqlite3", FixtureModel(), testing=True, auth_file=credential["config"])) as c:
        for url in ("/health", "/ready", "/api/cases"):
            assert c.get(url).status_code == 401
        assert c.get("/health", auth=("test-operator", "wrong")).status_code == 401
        assert c.get("/health", auth=("test-operator", key)).json()["mode"] == "local_personal"
        c.auth = ("test-operator", key)
        session = c.post("/api/demo").json()
        case = c.get("/api/cases").json()[0]
        assert c.post(f'/api/cases/{case["id"]}/release', json={"evidence_version": 1}).status_code == 403
        c.headers["x-recase-csrf"] = session["csrf"]
        assert c.post(f'/api/cases/{case["id"]}/release', json={"evidence_version": 1}).status_code == 200
        config = tmp_path / "credential/auth.json"
        config.write_text(config.read_text() + "\n")
        assert c.get("/api/cases").status_code == 401  # Revoked without restart.


def test_insecure_credential_files_and_missing_personal_config_are_refused(tmp_path, monkeypatch):
    config = provision(tmp_path / "credential", "test")["config"]
    from pathlib import Path
    Path(config).chmod(0o644)
    with pytest.raises(PermissionError):
        LocalAuth(config)
    monkeypatch.setenv("RECASE_MODE", "personal")
    monkeypatch.delenv("RECASE_AUTH_FILE", raising=False)
    with pytest.raises(RuntimeError, match="requires"):
        create_app(tmp_path / "new.db", FixtureModel(), testing=True)


def test_browser_form_login_cookie_error_origin_and_restart_expiry(tmp_path):
    credential = provision(tmp_path / "credential", "test-operator")
    key = (tmp_path / "credential/key.txt").read_text().strip()
    with TestClient(create_app(tmp_path / "db.sqlite3", FixtureModel(), testing=True, auth_file=credential["config"])) as c:
        page = c.get("/")
        assert 'name="access_key"' in page.text and page.headers["referrer-policy"] == "same-origin"
        assert c.get("/auth.css").status_code == 200
        wrong = c.post("/api/local-login", data={"access_key": "wrong"})
        assert wrong.status_code == 401 and "일치하지" in wrong.text
        assert 'aria-invalid="true"' in wrong.text and 'aria-describedby="key-hint login-error" autofocus' in wrong.text
        assert c.post("/api/local-login", data={"access_key": key}, headers={"origin": "https://evil.example"}).status_code == 403
        assert c.post("/api/local-login", data={"access_key": key}, headers={"origin": "null"}).status_code == 403
        assert c.post("/api/local-login", data={"access_key": "x" * 3000}).status_code == 413
        response = c.post("/api/local-login", data={"access_key": key}, follow_redirects=False)
        assert response.status_code == 303 and "HttpOnly" in response.headers["set-cookie"]
        assert c.get("/health").status_code == 200
        cookie = c.cookies.get("recase_local_auth")
        c.app.state.model.close()
    restarted_auth = LocalAuth(credential["config"])
    assert not restarted_auth.permits(session_cookie=cookie)
