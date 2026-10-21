"""Three real LangGraph subgraphs with private state and isolated tool failures."""
import asyncio
from functools import partial
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langsmith import traceable
from .retry import with_retry


class SpecialistState(TypedDict, total=False):
    targets: list[str]
    query: str
    mode: str
    scenario: str
    seed: list[dict]
    collected: list[dict]
    emit: object


def publish(result, emit=None):
    (emit or get_stream_writer())({"type": "TaskCompleted" if result["status"] == "completed" else "TaskFailed",
                         "source": result["source"], "target": result["target"], "id": result["id"],
                         "phase": result.get("phase"), "error": result.get("error"),
                         "retries": result.get("retries", 0), "evidence": result})
    return result


async def safe_tool(deps, source, target, tool, arguments, phase=None, emit=None):
    key = f"{source}:{target}" + (f":{phase}" if phase else "")
    async def bounded():
        return await asyncio.wait_for(deps.mcp.call_tool(tool, arguments), timeout=deps.settings.tool_timeout)
    try:
        data, retries = await with_retry(bounded, retries=2, base_delay=0.05)
        if data.get("system_name") != target:
            raise ValueError("조회 결과의 시스템명이 요청 대상과 다릅니다.")
        if source in ("monitoring", "snapshot"):
            from .contracts import SystemStatus
            data = SystemStatus.model_validate(data).model_dump()
        elif source == "logs":
            from .contracts import LogResult
            data = LogResult.model_validate(data).model_dump()
        return publish({"id": key, "source": source, "target": target, "phase": phase,
                "status": "completed", "data": data, "retries": retries}, emit)
    except Exception as exc:
        return publish({"id": key, "source": source, "target": target, "phase": phase,
                "status": "failed", "error": "조회 시간 초과" if isinstance(exc, TimeoutError) else str(exc)[:240],
                "retries": 1 if isinstance(exc, TimeoutError) else 0}, emit)


@traceable(name="metrics_specialist.collect")
async def metric_collect(state, deps):
    specs = []
    for target in state["targets"]:
        if state.get("mode") == "deployment":
            specs += [("snapshot", target, "get_deployment_snapshot", {"system_name": target, "scenario": state["scenario"], "phase": phase}, phase) for phase in ("before", "after")]
        else:
            specs.append(("monitoring", target, "get_monitoring_status", {"system_name": target}, None))
    seed = {c["id"]: c for c in state.get("seed", []) if c["status"] == "completed"}
    async def one(spec):
        source, target, tool, args, phase = spec
        key = f"{source}:{target}" + (f":{phase}" if phase else "")
        return seed[key] if key in seed else await safe_tool(deps, source, target, tool, args, phase, emit=state.get("emit"))
    return {"collected": list(await asyncio.gather(*(one(s) for s in specs)))}


@traceable(name="logs_specialist.collect")
async def log_collect(state, deps):
    seed = {c["id"]: c for c in state.get("seed", []) if c["status"] == "completed"}
    async def one(t):
        return seed.get(f"logs:{t}") or await safe_tool(deps, "logs", t, "get_recent_logs", {"system_name": t}, emit=state.get("emit"))
    return {"collected": list(await asyncio.gather(*(one(t) for t in state["targets"])))}


@traceable(name="runbook_specialist.retrieve")
async def runbook_collect(state, deps):
    try:
        docs = await asyncio.wait_for(asyncio.to_thread(deps.retriever.search, state["query"], deps.settings.rag_top_k), timeout=deps.settings.tool_timeout * 3)
        server, template = await asyncio.wait_for(deps.mcp.find_resource_template("get_incident_runbook"), deps.settings.tool_timeout)
        seed = {c["id"]: c for c in state.get("seed", []) if c["status"] == "completed" and c["source"] == "runbook"}
        async def one(doc):
            if doc["id"] in seed and seed[doc["id"]]["data"]["text"] == doc["text"]:
                return seed[doc["id"]]
            try:
                body = await asyncio.wait_for(deps.mcp.read_resource(template.format(incident_type=doc["id"][2:]), server=server), deps.settings.tool_timeout)
                if body.strip() != doc["text"].strip():
                    raise ValueError("검색 인덱스와 MCP Resource 본문이 일치하지 않습니다.")
                return publish({"id": doc["id"], "source": "runbook", "target": doc["uri"], "status": "completed", "data": doc}, state.get("emit"))
            except Exception as exc:
                return publish({"id": doc["id"], "source": "runbook", "target": doc["uri"], "status": "failed", "error": str(exc)[:200]}, state.get("emit"))
        collected = list(await asyncio.gather(*(one(d) for d in docs)))
        if not docs:
            collected = [{"id": "rag:search", "source": "runbook", "target": "semantic-search", "status": "failed", "error": "관련 문서 정보 부족: 유사도 기준 미달"}]
        return {"collected": collected}
    except Exception as exc:
        return {"collected": [{"id": "rag:search", "source": "runbook", "target": "semantic-search", "status": "failed", "error": str(exc)[:200] or "검색 시간 초과"}]}


def build_specialists(deps):
    graphs = {}
    for name, collect in (("metrics", metric_collect), ("logs", log_collect), ("runbooks", runbook_collect)):
        g = StateGraph(SpecialistState)
        g.add_node("collect", partial(collect, deps=deps))
        g.add_edge(START, "collect")
        g.add_edge("collect", END)
        graphs[name] = g.compile()
    return graphs
