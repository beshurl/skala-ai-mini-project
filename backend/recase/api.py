"""Loopback-only local demo with cookie auth, CSRF, persisted jobs and SSE."""
import asyncio
import fcntl
import json
import os
import secrets
import uuid
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Annotated

# Set before importing LangGraph. No external observability even if the parent shell has keys.
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["DO_NOT_TRACK"] = "1"

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from recase.mcp_client import connect
from recase.model import LocalModel
from recase.store import Store, NotFound, Conflict, TERMINAL
from recase.worker import Worker
from recase.accounts import Accounts
from recase.auth_api import routes as auth_routes
from recase.admin import routes as admin_routes
from fastapi.exceptions import RequestValidationError
from recase.observability import Observations, request_context
from recase.paths import PROJECT_ROOT, FRONTEND_ROOT, workspace_path

ROOT = PROJECT_ROOT


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_version: int = Field(ge=1)


class LifecycleRequest(VersionRequest):
    model_config = ConfigDict(extra="forbid", strict=True)
    lifecycle_revision: int = Field(ge=1)
    action: Literal["close", "reopen", "hold", "release_hold"]
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value):
        if not value.strip():
            raise ValueError("Explicit reason required")
        return value.strip()


class SyntheticEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=8000)
    kind: Literal["statement", "record", "note", "correction", "test_result"] = "record"
    initially_released: bool = True

    @field_validator("title", "text")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Explicit text required")
        return value.strip()


class SyntheticCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    creation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    synthetic_only: Literal[True]
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(max_length=2000)
    claims: list[Annotated[str, Field(min_length=1, max_length=700)]] = Field(min_length=1, max_length=8)
    evidence: list[SyntheticEvidence] = Field(min_length=1, max_length=24)

    @field_validator("title", "claims")
    @classmethod
    def meaningful(cls, value):
        values = value if isinstance(value, list) else [value]
        if any(not text.strip() for text in values):
            raise ValueError("Explicit claim/title required")
        return [v.strip() for v in value] if isinstance(value, list) else value.strip()

    @field_validator("evidence")
    @classmethod
    def source_budget(cls, value):
        if sum(len(e.text) for e in value) > 24000:
            raise ValueError("Synthetic evidence character budget exceeded")
        return value


def create_app(db_path=None, model=None, testing=False, deletions_file=None, accounts_path=None, frontend_dist=None):
    db_path = workspace_path(db_path or os.environ.get("RECASE_DB", ROOT / "runtime" / "recase.sqlite3")).resolve()
    if os.environ.get("RECASE_AUTH_FILE") or os.environ.get("RECASE_ADMIN_AUTH_FILE"):
        raise RuntimeError("ACCESS_KEY_AUTH_REMOVED: configure RECASE_ACCOUNTS_DB instead")
    accounts_path = workspace_path(accounts_path or os.environ.get("RECASE_ACCOUNTS_DB", db_path.with_name(db_path.stem + ".accounts.sqlite3")))
    explicit_deletions = deletions_file is not None or not testing and "RECASE_DELETIONS" in os.environ
    deletions_file = deletions_file or (None if testing else os.environ.get("RECASE_DELETIONS", ROOT / "runtime" / "deletions.jsonl"))
    deletions_file = workspace_path(deletions_file) if deletions_file else None

    @asynccontextmanager
    async def lifespan(app):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        lock = (db_path.parent / (db_path.name + ".server.lock")).open("a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise RuntimeError("SERVER_ALREADY_RUNNING: use one API worker") from None
        try:
            app.state.accounts = Accounts(accounts_path)
            store = Store(db_path)
            if deletions_file and Path(deletions_file).exists():
                from recase.retention import apply_deletions
                apply_deletions(db_path, deletions_file, revoke_all_sessions=False)
            elif not testing or explicit_deletions:
                raise RuntimeError("Account service requires an independent RECASE_DELETIONS journal")
            store.recover()
            app.state.store = store
            app.state.observations = Observations(db_path.with_name(db_path.name + ".observations.sqlite3"))
            selected = model
            if selected is None:
                backend = os.environ.get("RECASE_BACKEND", "mlx")
                if backend == "fixture":
                    from recase.testing import FixtureModel
                    selected = FixtureModel()
                elif backend == "mlx":
                    selected = LocalModel(adapter=os.environ.get("RECASE_ADAPTER", str(ROOT / "outputs" / "mlx_adapter")))
                else:
                    raise RuntimeError("UNSUPPORTED_BACKEND")
            app.state.ready, app.state.startup_error = False, None
            app.state.model = selected
            load_started = time.perf_counter()
            try:
                await asyncio.to_thread(selected.load)
            except Exception as error:
                app.state.startup_error = type(error).__name__
            app.state.observations.record(component="system", event="model_loaded", operation="load", duration_ms=(time.perf_counter()-load_started)*1000,
                                          outcome="ERROR" if app.state.startup_error else "SUCCESS", error="MODEL_LOAD_FAILED" if app.state.startup_error else None)
            async with connect(db_path, secrets.token_urlsafe(32), observations=app.state.observations) as mcp:
                app.state.mcp = mcp
                worker = Worker(store, mcp, selected, observations=app.state.observations)
                app.state.worker = worker
                worker.start()
                app.state.ready = app.state.startup_error is None
                try:
                    yield
                finally:
                    app.state.ready = False
                    await worker.stop()
            selected.close()
        finally:
            if hasattr(app.state, "accounts"):
                app.state.accounts.close()
            lock.close()

    app = FastAPI(title="RE:CASE local evidence simulator", lifespan=lifespan, docs_url="/api/docs" if testing else None, redoc_url=None, openapi_url="/api/openapi.json" if testing else None,
                  telemetry={"tracing": False, "metrics": False, "logs": False, "operation_spans": False, "auto_configure": False})
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"] if testing else ["localhost", "127.0.0.1", "[::1]"])

    async def boundary(request, call_next):
        request_id = request.state.request_id
        if not testing and request.client.host not in ("127.0.0.1", "::1"):
            return JSONResponse({"error": "LOCAL_DEMO_ONLY", "request_id": request_id}, 403)
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"error": "ORIGIN_DENIED", "request_id": request_id}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "ORIGIN_DENIED", "request_id": request_id}, 403)
        public_api = {"/api/auth/login", "/api/auth/register", "/api/auth/session"}
        if (request.url.path.startswith("/api/") and request.url.path not in public_api) or request.url.path == "/ready":
            try:
                app.state.accounts.require(request)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail, "request_id": request_id}, error.status_code)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        return response

    @app.middleware("http")
    async def observe_boundary(request, call_next):
        request.state.request_id = uuid.uuid4().hex
        context = request_context.set(request.state.request_id)
        started, status = time.perf_counter(), 500
        try:
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > 65536:
                        response = JSONResponse({"error": "REQUEST_TOO_LARGE"}, 413)
                        break
                    body.extend(chunk)
                else:
                    request._body = bytes(body)
                    response = await boundary(request, call_next)
            else:
                response = await boundary(request, call_next)
            status = response.status_code
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "UNMATCHED")
            if route in {"/{path:path}", "/cases", "/cases/{case_id}", "/admin", "/admin/{section}", "/history", "/settings"}:
                route = "SPA"
            elif request.url.path.startswith("/assets/"):
                route = "ASSET"
            if hasattr(app.state, "observations"):
                app.state.observations.record(component="http", event="request_finished", route=route, method=request.method, status=status,
                    duration_ms=(time.perf_counter()-started)*1000, trace_id=getattr(request.state, "trace_id", None),
                    outcome="ERROR" if status >= 400 else "SUCCESS", error=f"HTTP_{status}" if status >= 400 else None)
            request_context.reset(context)

    @app.exception_handler(NotFound)
    async def not_found(request, error):
        return JSONResponse({"error": "NOT_FOUND"}, 404)

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse({"error": str(error)}, 409)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Pydantic errors may contain the submitted password; never return those inputs.
        if request.url.path.startswith("/api/auth/"):
            return JSONResponse({"detail": "AUTH_INPUT_INVALID"}, 422)
        from fastapi.exception_handlers import request_validation_exception_handler
        return await request_validation_exception_handler(request, error)

    def session(request, write=False):
        return app.state.accounts.require(request, write=write)

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local_accounts"}

    @app.get("/ready")
    def ready():
        return JSONResponse({"ready": app.state.ready, "model": app.state.model.info, "error": app.state.startup_error}, 200 if app.state.ready else 503)

    @app.post("/api/demo", status_code=201)
    def demo(request: Request):
        account = session(request, True)
        app.state.store.seed_demo(account["user_id"])
        return {**account, "mode": "local_accounts"}

    @app.get("/api/session")
    def current_session(request: Request):
        return {**session(request), "mode": "local_accounts", "model": app.state.model.info}

    @app.post("/api/demo/new", status_code=201)
    def new_demo(request: Request):
        account = session(request, True)
        app.state.store.seed_demo(account["user_id"], fresh=True)
        return {**account, "mode": "local_accounts"}

    @app.get("/api/cases")
    def cases(request: Request):
        return app.state.store.cases(session(request)["user_id"])

    @app.post("/api/cases", status_code=201)
    def create_synthetic(body: SyntheticCase, request: Request):
        account = session(request, True)
        return app.state.store.create_synthetic_case(account["user_id"], body.creation_id, body.title, body.summary, body.claims,
                                                     [e.model_dump() for e in body.evidence])

    @app.post("/api/practice/general", status_code=201)
    def general_practice(request: Request):
        from recase.practice import seed_practice
        account = session(request, True)
        return seed_practice(app.state.store, account["user_id"], general=True)

    @app.post("/api/practice", status_code=201)
    def practice(request: Request):
        from recase.practice import seed_practice
        account = session(request, True)
        return seed_practice(app.state.store, account["user_id"])

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, request: Request):
        return app.state.store.snapshot(session(request)["user_id"], case_id)

    @app.get("/api/cases/{case_id}/lifecycle")
    def case_lifecycle(case_id: str, request: Request):
        return app.state.store.lifecycle(session(request)["user_id"], case_id)

    @app.post("/api/cases/{case_id}/lifecycle")
    def change_lifecycle(case_id: str, body: LifecycleRequest, request: Request):
        return app.state.store.transition_case(session(request, True)["user_id"], case_id,
            body.evidence_version, body.lifecycle_revision, body.action, body.reason)

    @app.get("/api/cases/{case_id}/evidence/{evidence_id}")
    def evidence(case_id: str, evidence_id: str, request: Request):
        data = app.state.store.snapshot(session(request)["user_id"], case_id)
        for e in data["evidence"]:
            if e["id"] == evidence_id:
                return {**e, "evidence_version": data["evidence_version"], "start": 0, "end": len(e["text"])}
        raise NotFound()

    @app.post("/api/cases/{case_id}/release")
    def release(case_id: str, body: VersionRequest, request: Request):
        return app.state.store.release_next(session(request, True)["user_id"], case_id, body.evidence_version)

    @app.post("/api/cases/{case_id}/analyses", status_code=202)
    async def analyze(case_id: str, body: VersionRequest, request: Request):
        s = session(request, True)
        if not app.state.ready:
            raise HTTPException(503, detail="MODEL_NOT_READY")
        if app.state.worker.queue.full():
            raise HTTPException(429, detail="ANALYSIS_QUEUE_FULL")
        job = app.state.store.create_job(s["user_id"], case_id, body.evidence_version, app.state.model.info)
        request.state.trace_id = job["id"]
        app.state.worker.request_ids[job["id"]] = request.state.request_id
        app.state.worker.queue.put_nowait((s["user_id"], job["id"]))
        return job

    @app.get("/api/cases/{case_id}/analyses")
    def analyses(case_id: str, request: Request):
        return app.state.store.jobs(session(request)["user_id"], case_id)

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str, request: Request):
        return app.state.store.job(session(request)["user_id"], job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str, request: Request):
        s = session(request, True)
        app.state.worker.cancel(s["user_id"], job_id)
        return app.state.store.job(s["user_id"], job_id)

    @app.get("/api/jobs/{job_id}/events")
    async def events(job_id: str, request: Request):
        s = session(request)
        app.state.store.job(s["user_id"], job_id)
        try:
            after = max(0, int(request.headers.get("last-event-id", request.query_params.get("after", "0"))))
        except ValueError:
            raise HTTPException(400, detail="INVALID_EVENT_ID") from None

        async def stream():
            cursor = after
            while True:
                if await request.is_disconnected():
                    return
                try:
                    app.state.accounts.require(request)
                except HTTPException:
                    return
                rows = app.state.store.events(s["user_id"], job_id, cursor)
                for row in rows:
                    cursor = row["id"]
                    yield f'id: {cursor}\nevent: {row["type"]}\ndata: {json.dumps({"job_id": job_id, **row}, ensure_ascii=False)}\n\n'
                if app.state.store.job(s["user_id"], job_id)["status"] in TERMINAL:
                    return
                yield ": keepalive\n\n"
                await asyncio.sleep(.25)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})

    @app.get("/api/cases/{case_id}/compare")
    def compare_results(case_id: str, before: str, after: str, request: Request):
        owner = session(request)["user_id"]
        app.state.store.snapshot(owner, case_id)
        a, b = (app.state.store.job(owner, i) for i in (before, after))
        if any(j["case_id"] != case_id or not j["result"] for j in (a, b)):
            raise Conflict("COMPARABLE_RESULTS_REQUIRED")
        if a["id"] == b["id"] or a["created"] >= b["created"]:
            raise Conflict("CHRONOLOGICAL_RESULTS_REQUIRED")
        left = {f["claim_id"]: f for f in a["result"]["findings"]}
        changes = [{"claim_id": f["claim_id"], "before": left.get(f["claim_id"]), "after": f,
                    "changed": left.get(f["claim_id"], {}).get("label") != f["label"]} for f in b["result"]["findings"]]
        return {"case_id": case_id, "before_version": a["version"], "after_version": b["version"], "findings": changes,
                "model_changed": a["model"] != b["model"],
                "analysis_contract_changed": a["result"].get("analysis_contract_version","legacy-relation-v2") != b["result"].get("analysis_contract_version","legacy-relation-v2"),
                "reason": "공개 증거 버전·분석 방식과 각 결과의 근거를 대조하세요."}

    app.include_router(auth_routes())
    app.include_router(admin_routes())

    dist = workspace_path(frontend_dist or os.environ.get("RECASE_FRONTEND_DIST", FRONTEND_ROOT / "dist"))
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/login", include_in_schema=False)
    @app.get("/signup", include_in_schema=False)
    @app.get("/admin/{section}", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/settings", include_in_schema=False)
    @app.get("/history", include_in_schema=False)
    @app.get("/cases/{case_id}", include_in_schema=False)
    @app.get("/cases", include_in_schema=False)
    @app.get("/")
    def index():
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return JSONResponse({"error": "FRONTEND_NOT_BUILT", "command": "cd frontend && npm ci && npm run build"}, 503)

    return app


app = create_app()
