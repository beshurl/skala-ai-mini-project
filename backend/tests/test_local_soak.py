import asyncio

import httpx
import pytest

from scripts import local_soak_check as soak


def transport(mode="complete"):
    calls = []
    model = {"backend": "mlx", "adapter_loaded": True}

    def handle(request):
        path = request.url.path
        calls.append((request.method, path))
        if path == "/ready":
            return httpx.Response(200, json={"ready": True, "model": model})
        if path == "/health":
            return httpx.Response(200, json={"mode": "local_personal"})
        if path == "/api/demo":
            return httpx.Response(201, json={"csrf": "synthetic-test-csrf"})
        if path == "/api/cases":
            return httpx.Response(200, json=[{"id": "fixture-case"}])
        if path == "/api/cases/fixture-case":
            return httpx.Response(200, json={"source": "synthetic_fixture" if mode != "real_case" else "actual_judgment"})
        if path.endswith("/analyses"):
            return httpx.Response(202, json={"id": "only-this-check-job"})
        if path.endswith("/cancel"):
            return httpx.Response(200, json={})
        if path == "/api/jobs/only-this-check-job":
            return httpx.Response(200, json={"status": "RUNNING" if mode == "stalled" else "COMPLETED",
                                           "result": {"provenance": "local_mlx", "usage": {"model_calls": 1}}})
        return httpx.Response(404)
    return httpx.MockTransport(handle), calls


def test_complete_window_reports_real_terminal_counts_not_requested_counts(monkeypatch):
    monkeypatch.setattr(soak, "process_sample", lambda *_: {"uid": 499, "rss_kib": 100, "cpu_percent": 0.0})
    mocked, calls = transport()
    result = asyncio.run(soak.run("http://127.0.0.1", ("fixture", "test"), 1, 499, .03, .01, 2, .02, transport=mocked))
    assert result["status"] == "PASS" and result["full_requested_window_observed"]
    assert result["completed_jobs"] == result["model_calls"] == 2
    assert not any(path.endswith("/cancel") for _, path in calls)


def test_stalled_job_fails_once_and_cancels_only_own_job(monkeypatch):
    monkeypatch.setattr(soak, "process_sample", lambda *_: {"uid": 499, "rss_kib": 100, "cpu_percent": 0.0})
    mocked, calls = transport("stalled")
    result = asyncio.run(soak.run("http://localhost", ("fixture", "test"), 1, 499, 1, .01, 10, .02, transport=mocked))
    assert result["status"] == "FAIL" and result["error_code"] == "NO_JOB_PROGRESS_WITHIN_BUDGET"
    assert result["completed_jobs"] == result["model_calls"] == 0
    assert calls.count(("POST", "/api/cases/fixture-case/analyses")) == 1
    assert calls.count(("POST", "/api/jobs/only-this-check-job/cancel")) == 1


def test_non_synthetic_case_is_refused_before_submission(monkeypatch):
    monkeypatch.setattr(soak, "process_sample", lambda *_: {"uid": 499, "rss_kib": 100, "cpu_percent": 0.0})
    mocked, calls = transport("real_case")
    result = asyncio.run(soak.run("http://localhost", ("fixture", "test"), 1, 499, 1, .01, 1, .02, transport=mocked))
    assert result["status"] == "FAIL" and result["error_code"] == "SYNTHETIC_CASE_REQUIRED"
    assert not any(path.endswith("/analyses") for _, path in calls)


def test_account_login_csrf_fresh_cases_logout_and_secret_free_report(monkeypatch):
    import json
    monkeypatch.setattr(soak, "process_sample", lambda *_: {"uid": 499, "rss_kib": 100, "cpu_percent": 0.0})
    legacy, calls = transport()
    seen = []
    def handle(request):
        seen.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"mode": "local_accounts"})
        if request.url.path == "/api/auth/login":
            return httpx.Response(200, json={"csrf": "fixture-csrf"}, headers={"set-cookie":"recase_account=fixture-cookie; Path=/"})
        if request.url.path in {"/api/demo/new", "/api/auth/logout"}:
            assert request.headers["x-recase-csrf"] == "fixture-csrf"
            assert "fixture-cookie" in request.headers["cookie"]
            return httpx.Response(201 if request.url.path.endswith("new") else 200, json={"csrf":"fixture-csrf"})
        return legacy.handle_request(request)
    credentials={"email":"fixture@example.test", "password":"SYNTHETIC_SOAK_PASSWORD"}
    result=asyncio.run(soak.run("http://localhost", None, 1, 499, .02, .01, 1, .02,
                              transport=httpx.MockTransport(handle), account_credentials=credentials))
    assert result["status"] == "PASS" and result["authentication_mode"] == "account-password"
    assert [r.url.path for r in seen].count("/api/demo/new") == 1
    assert seen[-1].url.path == "/api/auth/logout"
    assert all(value not in json.dumps(result) for value in [credentials["password"], "fixture-cookie", "fixture-csrf"])


def test_auth_mode_mismatch_refuses_credentials_and_job_submission(monkeypatch):
    monkeypatch.setattr(soak, "process_sample", lambda *_: {"uid": 499, "rss_kib": 100, "cpu_percent": 0.0})
    mocked, calls = transport()
    result=asyncio.run(soak.run("http://localhost", None, 1, 499, .02, .01, 1, .02, transport=mocked,
                              account_credentials={"email":"fixture@example.test", "password":"not-sent"}))
    assert result["error_code"] == "AUTHENTICATION_MODE_MISMATCH"
    assert calls == [("GET", "/health")]


@pytest.mark.parametrize("url", ["https://example.com", "http://localhost/?secret=x", "http://user:pass@127.0.0.1", "http://127.0.0.1/path"])
def test_external_targets_credentials_and_nonroot_urls_are_refused(url):
    with pytest.raises(ValueError):
        soak.validate(url, 600, 10, 60, 30)
