"""Separate local operator role. Read-only metadata APIs; never arbitrary tool execution."""
import re
import time
from fastapi import APIRouter, HTTPException, Query, Request
from recase.observability import COMPONENTS, TOOLS


def routes():
    router = APIRouter(prefix="/api/admin")

    def require(request):
        return request.app.state.accounts.require(request, admin=True)

    @router.get("/session")
    def session(request: Request):
        return require(request)

    @router.get("/summary")
    def summary(request: Request, seconds: int = Query(3600, ge=60, le=604800)):
        require(request)
        state = request.app.state
        info = {key: state.model.info.get(key) for key in ("backend", "model", "revision", "adapter_loaded", "prompt_version")}
        # Known safe identifiers, never a caller-supplied model filesystem path.
        if info["model"] not in {"mlx-community/Qwen3-4B-4bit", "deterministic-test-fixture"}:
            info["model"] = "local-model"
        if not isinstance(info["revision"], str) or not re.fullmatch(r"[a-zA-Z0-9._-]{1,64}", info["revision"]):
            info["revision"] = "UNVERIFIED"
        return {**state.observations.summary(seconds), "ready": state.ready, "model": info,
                "mcp_connected": state.mcp is not None, "tools": sorted(TOOLS),
                "queue_size": state.worker.queue.qsize(), "active_jobs": len(state.worker.active), "cpu": None, "memory": None,
                "search": {"method": "keyword-bigram-v1", "reference_corpus": "BLOCKED", "vector": False, "hybrid": False, "rerank": False}}

    @router.get("/logs")
    def logs(request: Request, seconds: int = Query(3600, ge=60, le=604800), component: str = Query("", max_length=12),
             level: str = Query("", max_length=8), q: str = Query("", max_length=80), request_id: str = Query("", max_length=32),
             trace_id: str = Query("", max_length=20), errors_only: bool = False, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)):
        require(request)
        if component and component not in COMPONENTS or level and level not in {"INFO", "WARN", "ERROR"}:
            raise HTTPException(422, detail="INVALID_LOG_FILTER")
        return request.app.state.observations.logs(since=time.time()-seconds, component=component, level=level, q=q,
                                                  request_id=request_id, trace_id=trace_id, errors_only=errors_only, limit=limit, offset=offset)

    return router
