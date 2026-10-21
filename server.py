"""Local operations API: one execution path for JSON and POST/GET SSE transports."""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4
from weakref import WeakValueDictionary
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal
from agent.deps import SupervisorDeps
from agent.settings import Settings
from agent.graph import build_graph
from agent.mcp_client import MCPClient
from agent.session_store import SqliteSessionStore
from agent.retrieval import RunbookIndex
from agent.targets import catalog
from agent.input_validation import normalize_message, validate_input
from agent.reporting import canonical_report, render_report
from agent.observability import normalize_tracing_env
TRACING_STATE = normalize_tracing_env()

CREATION_COUNT = 0


class IncidentDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onset: str = Field(default="", max_length=120)
    error_message: str = Field(default="", max_length=1000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=6000)
    thread_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    targets: list[str] = Field(default_factory=list, max_length=6)
    mode: Literal["helpdesk", "deployment"] = "helpdesk"
    scenario: Literal["stable", "cpu-rise", "new-alert", "missing-after"] = "stable"
    evidence_case: Literal["batch", "traffic", "release", "conflict", "missing"] = "batch"
    details: IncidentDetails = Field(default_factory=IncidentDetails)
    retry_record_id: str | None = Field(default=None, max_length=100)
    context_record_id: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def normalize_input(cls, value):
        value = normalize_message(value)
        if not value:
            raise ValueError("질문을 입력해주세요.")
        return value

def _build_llms():
    from agent.llm_runtime import build_models
    return build_models()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CREATION_COUNT
    settings = Settings()
    mcp = MCPClient()
    store = SqliteSessionStore(settings.db_path)
    retriever = RunbookIndex(settings.data_dir, settings.data_dir / "runbook_vectors.db", settings.embedding_model, settings.rag_backend)
    try:
        await mcp.start()
        backend, fast, quality = _build_llms()
        deps = SupervisorDeps(fast, quality, mcp, store, "v3-contrastive", settings, retriever)
        app.state.deps = deps
        app.state.graph = build_graph(deps)
        app.state.llm_backend = backend
        app.state.instance_id = id(deps)
        app.state.locks = WeakValueDictionary()
        CREATION_COUNT += 1
        yield
    finally:
        await mcp.stop()
        store.close()
        retriever.close()


app = FastAPI(title="운영 진단 워크스페이스", lifespan=lifespan)


@app.get("/health")
async def health():
    deps = app.state.deps
    return {"status": "ok", "instance_id": app.state.instance_id, "creation_count": CREATION_COUNT,
            "supervisor_version": deps.version, "llm_backend": app.state.llm_backend,
            "fast_llm": deps.fast_llm.name, "quality_llm": deps.quality_llm.name,
            "data_kind": "synthetic", "rag_model": deps.settings.embedding_model,
            "tracing_configured": TRACING_STATE["configured"], "tracing": TRACING_STATE}


@app.get("/evaluation")
async def evaluation():
    from agent.settings import ROOT
    path = ROOT / "artifacts" / "evaluation.json"
    if not path.exists():
        raise HTTPException(404, "평가 결과가 없습니다. python -m evaluation.run으로 생성하세요.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/evaluation/live")
async def live_evaluation():
    from agent.settings import ROOT
    path = ROOT / "artifacts" / "live_evaluation.json"
    if not path.exists():
        raise HTTPException(404, "실제 모델 평가 결과가 없습니다. python -m evaluation.live로 생성하세요.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/evaluation/investigation")
async def investigation_evaluation():
    from agent.settings import ROOT
    path = ROOT / "artifacts" / "investigation_evaluation.json"
    if not path.exists():
        raise HTTPException(404, "추가 조사 실제 평가 결과가 없습니다.")
    from evaluation.summary import investigation_summary
    return investigation_summary(json.loads(path.read_text(encoding="utf-8")))


@app.get("/version")
async def version():
    return {"supervisor_version": app.state.deps.version}


@app.get("/systems")
async def systems():
    try:
        return {"systems": list(catalog(app.state.deps.settings.data_dir)), "data_kind": "synthetic",
                "thresholds": app.state.deps.settings.thresholds()}
    except Exception as exc:
        raise HTTPException(503, f"시스템 목록 조회 실패: {exc}")


ThreadId = Query(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


@app.get("/sessions/{thread_id}")
async def session(thread_id: str):
    # Opaque browser UUIDs isolate local sessions; production authentication is separate.
    if not __import__('re').fullmatch(r"[A-Za-z0-9_-]{1,100}", thread_id):
        raise HTTPException(422, "잘못된 세션 ID")
    store = app.state.deps.session_store
    return {"messages": store.load(thread_id), "records": store.records(thread_id), "context": store.context(thread_id)}


def metadata(result, run_id=None):
    return {"route": result.get("route"), "status": result.get("status"), "targets": result.get("targets", []),
            "retry_count": result.get("retry_count", 0), "validation_attempts": result.get("validation_attempts", 0),
            "rewrites": max(0, result.get("validation_attempts", 0) - 1), "replan_rounds": result.get("replan_rounds", 0),
            "cost_usd_estimate": result.get("cost_usd", 0), "model_usage": result.get("model_usage", []), "tokens": result.get("tokens", 0), "elapsed_ms": result.get("elapsed_ms"),
            "llm_backend": app.state.llm_backend, "supervisor_version": app.state.deps.version,
            "langsmith_run_id": run_id, "record_id": result.get("record_id"), "thread_id": result.get("thread_id")}


async def deadline_stream(stream, seconds):
    """An absolute deadline remains valid across async-generator yields and trace tasks."""
    deadline = time.perf_counter() + seconds
    try:
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("request deadline exceeded")
            try:
                item = await asyncio.wait_for(anext(stream), timeout=remaining)
            except StopAsyncIteration:
                break
            yield item
    finally:
        await stream.aclose()


@traceable(name="chat_request")
async def execute(req):
    deps = app.state.deps
    lock = app.state.locks.get(req.thread_id)
    if lock is None:
        lock = asyncio.Lock()
        app.state.locks[req.thread_id] = lock
    async with lock:
        state = {"query": req.message, "thread_id": req.thread_id, "history": deps.session_store.memory(req.thread_id),
                 "context": deps.session_store.context(req.thread_id), "selected_targets": req.targets,
                 "mode": req.mode, "scenario": req.scenario, "evidence_case": req.evidence_case, "details": req.details.model_dump(),
                 "events": [], "cost_usd": 0.0, "tokens": 0}
        if req.context_record_id:
            past = deps.session_store.record(req.thread_id, req.context_record_id)
            if not past or not past.get("report"):
                yield {"type": "Error", "message": "후속 질문의 원래 조사 기록을 찾지 못했습니다. 같은 대화의 결과를 선택해주세요."}
                return
            question = past["report"]["question"]
            state["context"] = {"targets": past["targets"], "last_question": question, "original_question": question,
                                "details": past.get("details", {})}
        if req.retry_record_id:
            record = deps.session_store.record(req.thread_id, req.retry_record_id)
            if not record:
                yield {"type": "Error", "message": "재시도할 기록을 찾지 못했습니다. 같은 대화의 기록을 선택해주세요."}
                return
            original_report = record.get("report") or {}
            if set(req.targets) != set(record["targets"]) or req.mode != record["mode"] or req.message != original_report.get("question") or req.scenario != record.get("scenario", "stable") or req.evidence_case != record.get("evidence_case", "batch"):
                yield {"type": "Error", "message": "재시도는 원래 기록의 질문·대상·점검 방식에서만 가능합니다."}
                return
            state["context"] = {"targets": record["targets"], "last_question": original_report["question"], "original_question": original_report["question"], "details": record.get("details", {})}
            state["seed_collected"] = [c for c in record.get("collected", []) if c.get("status") == "completed"]
            state["collected"] = list(state["seed_collected"])
        try:
            known = catalog(deps.settings.data_dir)
        except Exception:
            known = {}  # The existing resolve node reports catalog failures without a model call.
        admission = validate_input(req.message, known, state["context"], req.targets)
        if not admission["passed"]:
            event = {"type": "InputRejected", "code": admission["code"], "message": admission["reason"],
                     "tokens": 0, "llm_called": False}
            yield event
            state.update(route="reject", status="rejected", targets=[])
            rt = get_current_run_tree()
            yield {"type": "FinalAnswer", "reply": admission["message"], "report": None,
                   "validation": None, "input_validation": admission, "events": [event],
                   "metadata": {**metadata(state, str(rt.id) if rt else None), "llm_called": False}}
            return  # Rejected text must not enter SQLite memory or the next model prompt.
        started = time.perf_counter()
        seen = 0
        timeline = []
        try:
            async for mode, payload in deadline_stream(app.state.graph.astream(state, stream_mode=["updates", "custom"]), deps.settings.request_timeout):
                if mode == "custom":
                    timeline.append(payload)
                    if payload.get("investigation"):
                        state["investigation"] = payload["investigation"]
                    if payload.get("evidence"):
                        current = {c["id"]: c for c in state.get("collected", [])}
                        current[payload["evidence"]["id"]] = payload["evidence"]
                        state["collected"] = list(current.values())
                    yield payload
                    continue
                for node, delta in payload.items():
                    if not isinstance(delta, dict):
                        continue
                    state.update(delta)
                    for ev in delta.get("events", [])[seen:]:
                        emitted = {**ev, "node": node}
                        timeline.append(emitted)
                        yield emitted
                    if "events" in delta:
                        seen = len(delta["events"])
        except asyncio.CancelledError:
            if state.get("collected"):
                state["report"] = canonical_report(state, deps.settings)
                state["report"]["hypotheses"] = []
                state["report"]["recommendations"] = []
                state["validation"] = {"passed": False, "errors": ["요청 중단"], "attempts": state.get("validation_attempts", 0), "rewrites": max(0, state.get("validation_attempts", 0)-1), "checks": []}
                state["final"] = "연결 중단 전 확인한 결과\n" + render_report(state["report"], False)
                state["status"] = "interrupted"
                deps.session_store.save_turn(req.thread_id, req.message, state)
            raise
        except Exception as exc:
            state["report"] = canonical_report(state, deps.settings)
            state["report"]["hypotheses"] = []
            state["report"]["recommendations"] = []
            message = "요청 처리 시간이 초과되었습니다." if isinstance(exc, TimeoutError) else "조사 중 오류가 발생했습니다."
            state["report"]["limitations"].append(message)
            state["final"] = render_report(state["report"], False)
            state["status"] = "failed"
            state["validation"] = {"passed": False, "errors": [message], "attempts": state.get("validation_attempts", 0), "rewrites": max(0, state.get("validation_attempts", 0)-1), "checks": []}
            yield {"type": "Error", "message": message, "partial": True}
        if timeline:
            state["events"] = timeline
        state["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        state["record_id"] = deps.session_store.save_turn(req.thread_id, req.message, state)
        rt = get_current_run_tree()
        yield {"type": "FinalAnswer", "reply": state["final"], "report": state.get("report"),
               "validation": state.get("validation"), "events": state.get("events", []),
               "metadata": metadata(state, str(rt.id) if rt else None)}


@app.post("/chat")
async def chat(req: ChatRequest):
    events = []
    final = None
    async for item in execute(req):
        if item["type"] == "FinalAnswer":
            final = {k: v for k, v in item.items() if k != "type"}
        else:
            events.append(item)
    if final is not None:
        return final
    raise HTTPException(409, events[-1].get("message", "요청을 완료하지 못했습니다."))


def stream_response(req):
    async def gen():
        async for item in execute(req):
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/chat/stream")
async def chat_stream_post(req: ChatRequest):
    return stream_response(req)


@app.get("/chat/stream")
async def chat_stream(message: str = Query(min_length=1, max_length=6000), thread_id: str = ThreadId):
    return stream_response(ChatRequest(message=message, thread_id=thread_id))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("AGENT_PORT", "8100")), log_level="warning")
