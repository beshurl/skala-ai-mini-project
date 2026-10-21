"""Supervisor: resolve → parallel collection → contrastive investigation → validate.

Operational authority belongs to the catalog and typed tool results, never model plans.
"""
import asyncio
import json
from functools import partial
from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langsmith import traceable
from .targets import catalog, resolve_request
from .prompts import CHAT_SYSTEM_PROMPT
from .specialists import build_specialists
from .investigation import plan_investigation, probe_investigation, adjudicate_investigation
from .reporting import canonical_report, write_selection, apply_selection, render_report, call_model
from .validation import validate_selection


class AgentState(TypedDict, total=False):
    query: str
    thread_id: str
    history: list[dict]
    context: dict
    selected_targets: list[str]
    targets: list[str]
    unknown_targets: list[str]
    effective_query: str
    route: str
    mode: str
    scenario: str
    evidence_case: str
    investigation: dict
    details: dict
    scope_conflict: bool
    procedure: str
    seed_collected: list[dict]
    collected: list[dict]
    events: list[dict]
    report: dict
    draft: Any
    validation: dict
    validation_attempts: int
    validation_feedback: str
    replan_rounds: int
    final: str
    status: str
    cost_usd: float
    tokens: int
    retry_count: int
    model_usage: list[dict]


def event(state, *items):
    return state.get("events", []) + list(items)


@traceable(name="supervisor.resolve")
async def resolve_node(state, deps):
    try:
        known = catalog(deps.settings.data_dir)
    except Exception as exc:
        return {"route": "clarify", "final": f"시스템 목록을 읽지 못했습니다: {exc}. 환경을 확인한 뒤 다시 시도하세요.",
                "status": "needs_clarification", "events": event(state, {"type": "CatalogFailed", "error": str(exc)})}
    result = resolve_request(state["query"], known, state.get("context", {}), state.get("selected_targets", []), state.get("mode", "helpdesk"))
    context = result["context"]
    if result["route"] == "clarify" and context.get("pending"):
        context["pending"]["scenario"] = state.get("scenario", "stable")
        context["pending"]["evidence_case"] = state.get("evidence_case", "batch")
    elif result["route"] == "incident" and state.get("context", {}).get("pending"):
        result["scenario"] = state["context"]["pending"].get("scenario", state.get("scenario", "stable"))
        result["evidence_case"] = state["context"]["pending"].get("evidence_case", state.get("evidence_case", "batch"))
    previous_details = context.get("details", {}) if result.get("targets") == state.get("context", {}).get("targets") or result["route"] == "clarify" or state.get("context", {}).get("pending") else {}
    details = {**previous_details, **{k: v for k, v in state.get("details", {}).items() if v}}
    context["details"] = details
    result["details"] = details
    if result["route"] == "clarify":
        unknown = result.get("unknown_targets", [])
        text = ("질문에 적은 대상과 선택 목록이 다릅니다. 조사할 시스템을 일치시켜주세요. " if result.get("scope_conflict") else (f"미등록 시스템: {', '.join(unknown)}. " if unknown else "조사 대상이 명확하지 않습니다. "))
        result["final"] = text + f"등록된 시스템({', '.join(known)})에서 대상을 선택해주세요. 원래 질문은 유지합니다. 증상, 발생 시각, 오류 메시지(없으면 없음)도 알려주세요."
        result["status"] = "needs_clarification"
    return {**result, "events": event(state, {"type": "TargetResolved", "route": result["route"], "targets": result["targets"], "unknown": result.get("unknown_targets", [])})}


async def chat_node(state, deps):
    if hasattr(deps.fast_llm, "achat"):
        reply, usage = await asyncio.wait_for(call_model(deps.fast_llm,
            CHAT_SYSTEM_PROMPT,
            json.dumps({"history": state.get("history", []), "message": state["query"]}, ensure_ascii=False)), deps.settings.llm_timeout)
    else:
        reply, usage = await deps.fast_llm.chat(state["query"], state.get("history", []))
    return {"final": reply, "status": "completed", "cost_usd": usage.get("usd", 0), "tokens": usage.get("tokens", 0),
            "model_usage": [usage],
            "events": event(state, {"type": "Finalize", "pipeline": "chat-direct"})}


async def plan_node(state, deps):
    events = event(state, {"type": "PlanCreated", "targets": state["targets"], "specialists": ["metrics", "logs", "runbooks"], "mode": state["mode"]})
    procedure = "기본 읽기 전용 진단 절차"
    try:
        server = await asyncio.wait_for(deps.mcp.find_prompt("incident_analysis_prompt"), deps.settings.tool_timeout)
        procedure = await asyncio.wait_for(deps.mcp.get_prompt("incident_analysis_prompt", {"system_name": ", ".join(state["targets"]), "symptom": state["effective_query"]}, server=server), deps.settings.tool_timeout)
        events.append({"type": "ProcedureLoaded", "source": "MCP Prompt"})
    except Exception as exc:
        events.append({"type": "ProcedureUnavailable", "error": str(exc)[:160], "fallback": "기본 읽기 전용 절차"})
    return {"events": events, "procedure": procedure}


@traceable(name="supervisor.parallel_research")
async def research_node(state, specialists):
    writer = get_stream_writer()
    async def one(name, graph, query=None):
        writer({"type": "SpecialistStatus", "specialist": name, "status": "running"})
        try:
            result = await graph.ainvoke({"targets": state["targets"], "query": query or state["effective_query"], "mode": state["mode"], "scenario": state.get("scenario", "stable"), "seed": state.get("seed_collected", []), "emit": writer})
            collected = result.get("collected", [])
            status = "failed" if all(c["status"] == "failed" for c in collected) else ("partial" if any(c["status"] == "failed" for c in collected) else "completed")
        except Exception as exc:
            collected = [{"id": name + ":error", "source": name, "target": name, "status": "failed", "error": str(exc)[:200]}]
            status = "failed"
        writer({"type": "SpecialistStatus", "specialist": name, "status": status})
        seeded = {c["id"] for c in state.get("seed_collected", [])}
        for c in collected:
            if c["id"] in seeded or c["id"] == "rag:search" or c["source"] not in ("monitoring", "snapshot", "logs", "runbook"):
                writer({"type": "TaskCompleted" if c["status"] == "completed" else "TaskFailed", "source": c["source"], "target": c["target"], "phase": c.get("phase"), "id": c["id"], "error": c.get("error"), "retries": c.get("retries", 0), "reused": c["id"] in seeded, "evidence": c})
        return collected
    # Search once with actual observations, rather than repeating a blind search
    # and an alert-only search. Metrics and logs remain independent parallel reads.
    groups = await asyncio.gather(*(one(n, specialists[n]) for n in ("metrics", "logs")))
    observations = [c["data"] for group in groups for c in group if c["source"] in ("monitoring", "snapshot") and c["status"] == "completed"]
    query = state["effective_query"] + "\n관측 정보:\n" + "\n".join(
        f"상태 {d['status']}; CPU {d['cpu_percent']}%; memory {d['memory_percent']}%; {'; '.join(d['alerts'])}" for d in observations)
    groups.append(await one("runbooks", specialists["runbooks"], query))
    collected = [c for group in groups for c in group]
    return {"collected": collected, "retry_count": sum(c.get("retries", 0) for c in collected),
            "events": event(state, {"type": "ResearchCompleted", "succeeded": sum(c["status"] == "completed" for c in collected), "failed": sum(c["status"] == "failed" for c in collected)})}


async def analyze_node(state, deps):
    report = canonical_report(state, deps.settings)
    return {"report": report, "events": event(state, {"type": "EvidenceReady", "facts": len(report["facts"]), "runbooks": [{k: d[k] for k in ("id", "title", "uri", "score")} for d in report["runbooks"]], "verdict": report["verdict"]})}


async def write_node(state, deps):
    attempt = state.get("validation_attempts", 0) + 1
    try:
        draft, usage = await asyncio.wait_for(write_selection(deps.quality_llm, state["report"], state.get("validation_feedback", "")), timeout=deps.settings.llm_timeout)
    except Exception as exc:
        draft, usage = {"error": str(exc)[:200]}, {}
    # Drafts are internal. Only validation-completed reports leave the server.
    return {"draft": draft, "cost_usd": round(state.get("cost_usd", 0) + usage.get("usd", 0), 6),
            "tokens": state.get("tokens", 0) + usage.get("tokens", 0),
            "model_usage": state.get("model_usage", []) + ([usage] if usage else []),
            "events": event(state, {"type": "DraftWritten", "attempt": attempt})}


async def validate_node(state, deps):
    errors = validate_selection(state["draft"], state["report"])
    attempt = state.get("validation_attempts", 0) + 1
    validation = {"passed": not errors, "attempts": attempt, "rewrites": attempt - 1, "errors": errors,
                  "checks": ["시스템명", "수치", "상태·알림", "근거 ID", "조치 조건", "필수 항목"]}
    return {"validation": validation, "validation_attempts": attempt, "validation_feedback": " / ".join(errors),
            "events": event(state, {"type": "Validation", "attempt": attempt, "verdict": "합격" if not errors else "불합격", "errors": errors})}


async def finalize_node(state):
    passed = state["validation"]["passed"]
    report = apply_selection(state["report"], state["draft"]) if passed else {**state["report"], "hypotheses": [], "recommendations": []}
    status = "validation_failed" if not passed else ("partial" if report["failures"] or report["verdict"] == "정보 부족" else "completed")
    return {"report": report, "final": render_report(report, passed), "status": status,
            "events": event(state, {"type": "Finalize", "pipeline": "incident-v2", "status": status})}


def build_graph(deps):
    specialists = build_specialists(deps)
    g = StateGraph(AgentState)
    for name, fn in (("resolve", resolve_node), ("chat", chat_node), ("plan", plan_node), ("analyze", analyze_node), ("write", write_node), ("validate", validate_node)):
        g.add_node(name, partial(fn, deps=deps))
    g.add_node("research", partial(research_node, specialists=specialists))
    g.add_node("investigate_plan", partial(plan_investigation, deps=deps))
    g.add_node("investigate_probe", partial(probe_investigation, deps=deps))
    g.add_node("investigate_test", adjudicate_investigation)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "resolve")
    g.add_conditional_edges("resolve", lambda s: "chat" if s["route"] == "chat" else (END if s["route"] == "clarify" else "plan"))
    g.add_edge("chat", END)
    for source, target in (("plan", "research"), ("research", "investigate_plan"), ("investigate_probe", "investigate_test"), ("analyze", "write"), ("write", "validate")):
        g.add_edge(source, target)
    g.add_conditional_edges("investigate_plan", lambda s: "analyze" if s["investigation"]["phase"] == "stopped" else "investigate_probe")
    g.add_conditional_edges("investigate_test", lambda s: "analyze" if s["investigation"]["phase"] == "stopped" else "investigate_plan")
    g.add_conditional_edges("validate", lambda s: "finalize" if s["validation"]["passed"] or s["validation_attempts"] >= deps.settings.max_attempts else "write")
    g.add_edge("finalize", END)
    return g.compile()
