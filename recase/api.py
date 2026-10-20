"""Loopback-only local demo with cookie auth, CSRF, persisted jobs and SSE."""
import asyncio
import fcntl
import json
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Set before importing LangGraph. No external observability even if the parent shell has keys.
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["DO_NOT_TRACK"] = "1"

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from recase.mcp_client import connect
from recase.model import LocalModel
from recase.store import Store, NotFound, Conflict, TERMINAL
from recase.worker import Worker

ROOT = Path(__file__).resolve().parents[1]


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_version: int = Field(ge=1)


def create_app(db_path=None, model=None, testing=False):
    db_path = Path(db_path or os.environ.get("RECASE_DB", ROOT / "runtime" / "recase.sqlite3")).resolve()

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
            store = Store(db_path)
            store.recover()
            app.state.store = store
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
            try:
                await asyncio.to_thread(selected.load)
            except Exception as error:
                app.state.startup_error = type(error).__name__
            async with connect(db_path, secrets.token_urlsafe(32)) as mcp:
                app.state.mcp = mcp
                worker = Worker(store, mcp, selected)
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
            lock.close()

    app = FastAPI(title="RE:CASE local evidence simulator", lifespan=lifespan, docs_url="/api/docs" if testing else None, redoc_url=None, openapi_url="/api/openapi.json" if testing else None,
                  telemetry={"tracing": False, "metrics": False, "logs": False, "operation_spans": False, "auto_configure": False})
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"] if testing else ["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def boundary(request, call_next):
        request_id = uuid.uuid4().hex
        if not testing and request.client.host not in ("127.0.0.1", "::1"):
            return JSONResponse({"error": "LOCAL_DEMO_ONLY", "request_id": request_id}, 403)
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"error": "ORIGIN_DENIED", "request_id": request_id}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "ORIGIN_DENIED", "request_id": request_id}, 403)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        return response

    @app.exception_handler(NotFound)
    async def not_found(request, error):
        return JSONResponse({"error": "NOT_FOUND"}, 404)

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse({"error": str(error)}, 409)

    def session(request, write=False):
        try:
            value = app.state.store.session(request.cookies.get("recase_session", ""))
        except NotFound:
            raise HTTPException(401, detail="DEMO_SESSION_REQUIRED") from None
        if write and not secrets.compare_digest(request.headers.get("x-recase-csrf", ""), value["csrf"]):
            raise HTTPException(403, detail="CSRF_REQUIRED")
        return value

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local_demo"}

    @app.get("/ready")
    def ready():
        return JSONResponse({"ready": app.state.ready, "model": app.state.model.info, "error": app.state.startup_error}, 200 if app.state.ready else 503)

    @app.post("/api/demo", status_code=201)
    def demo(request: Request):
        # Re-entering the explicit demo reuses a still-valid session.
        try:
            existing = app.state.store.session(request.cookies.get("recase_session", ""))
            return {"mode": "local_demo", "user_id": existing["user_id"], "csrf": existing["csrf"]}
        except NotFound:
            info = app.state.store.new_demo()
        response = JSONResponse({k: v for k, v in info.items() if k != "token"}, 201)
        response.set_cookie("recase_session", info["token"], httponly=True, samesite="strict", max_age=86400, path="/")
        return response

    @app.get("/api/session")
    def current_session(request: Request):
        s = session(request)
        return {"user_id": s["user_id"], "csrf": s["csrf"], "mode": "local_demo", "model": app.state.model.info}

    @app.post("/api/demo/new", status_code=201)
    def new_demo(request: Request):
        session(request, True)
        info = app.state.store.new_demo()
        response = JSONResponse({k: v for k, v in info.items() if k != "token"}, 201)
        response.set_cookie("recase_session", info["token"], httponly=True, samesite="strict", max_age=86400, path="/")
        return response

    @app.get("/api/cases")
    def cases(request: Request):
        return app.state.store.cases(session(request)["user_id"])

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, request: Request):
        return app.state.store.snapshot(session(request)["user_id"], case_id)

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
                app.state.store.session(request.cookies.get("recase_session", ""))
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
                "model_changed": a["model"] != b["model"], "reason": "공개 증거 버전과 각 결과의 근거를 대조하세요."}

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    def index():
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return JSONResponse({"error": "FRONTEND_NOT_BUILT", "command": "cd frontend && npm ci && npm run build"}, 503)

    return app


app = create_app()
