"""Real planner, real writer, separate Judge and remote read-back for contrastive tests.

No expected answer is sent to the planner or MCP. Cases keep the same CPU/logs;
only the additional observations change. Fault injection cases are identified.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv
load_dotenv()
from langsmith import traceable, tracing_context
from langsmith.run_helpers import get_current_run_tree

from agent.deps import SupervisorDeps
from agent.graph import build_graph
from agent.judge import judge_report
from agent.llm_runtime import build_models, build_judge
from agent.mcp_client import MCPClient
from agent.observability import tracing_client, tracing_status, verify_remote_run
from agent.retrieval import RunbookIndex
from agent.session_store import SqliteSessionStore
from agent.settings import Settings, ROOT


CASES = [
    {"id": "batch", "label": "같은 CPU · 중복 배치 교차 지지", "winner": "batch"},
    {"id": "traffic", "label": "배치 단서 반증 · 요청량 교차 지지", "winner": "traffic"},
    {"id": "release", "label": "두 대안 반증 · 릴리스 교차 지지", "winner": "release"},
    {"id": "conflict", "label": "작업 중첩과 CPU 기여 근거 상충", "winner": None},
    {"id": "missing", "label": "추가 관측 없음 · 판단 보류", "winner": None},
    {"id": "probe-failure", "label": "귀속 도구 시간 초과 · 원인 보류", "winner": None, "fault_injection": True},
]


SOURCE_FILES = ["agent/graph.py", "agent/investigation.py", "agent/reporting.py", "agent/prompts.py", "agent/judge.py",
                "agent/contracts.py", "agent/specialists.py", "agent/diagnostic_data.py", "mcp_server.py",
                "data/investigation_cases.json"]


def fingerprints():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES}


class RecordingMCP:
    def __init__(self, client, fail=False):
        self.client, self.fail, self.calls = client, fail, []
    async def call_tool(self, name, arguments, **kwargs):
        self.calls.append({"tool": name, "arguments": arguments})
        if self.fail and name == "get_diagnostic_evidence" and arguments["probe"] == "cpu-attribution":
            raise TimeoutError("intentional cpu-attribution timeout")
        return await self.client.call_tool(name, arguments, **kwargs)
    def __getattr__(self, name):
        return getattr(self.client, name)


@traceable(name="contrastive_evaluation_case", process_inputs=lambda v: {"case": v["case"]})
async def execute_case(case, deps, judge):
    events = []
    result = {}
    started = time.perf_counter()
    state = {"query": "payments-service CPU가 91%이고 중복 배치 경고가 있습니다. 실제 원인을 다른 가설과 구별해주세요.",
             "thread_id": "contrastive-evaluation", "history": [], "context": {}, "events": [], "mode": "helpdesk",
             "evidence_case": case["id"] if case["id"] != "probe-failure" else "batch",
             "details": {"onset": "2026-10-21 09:00~09:05", "error_message": "응답 지연"}}
    async for mode, payload in build_graph(deps).astream(state, stream_mode=["updates", "custom"]):
        if mode == "custom": events.append(payload)
        else:
            for delta in payload.values():
                if isinstance(delta, dict): result.update(delta)
    elapsed = round((time.perf_counter()-started)*1000, 2)
    judged = await judge_report(result, judge)
    rt = get_current_run_tree()
    return {"result": result, "stream_events": events, "elapsed_ms": elapsed, "judge": judged,
            "trace_id": str(rt.id) if rt else None}


def check_case(case, item, calls):
    result = item["result"]
    board = result["investigation"]
    hs = board["hypotheses"]
    winner = [h["kind"] for h in hs if h["status"] == "supported"]
    expected = [case["winner"]] if case["winner"] else []
    events = item["stream_events"]
    order_ok = all(next(i for i, e in enumerate(events) if e["type"] == "ProbePlanned" and e["step"]["probe_id"] == s["probe_id"])
                   < next(i for i, e in enumerate(events) if e["type"] == "ProbeObserved" and e["step"]["probe_id"] == s["probe_id"])
                   for s in board["steps"])
    checks = {
        "same_cpu_preserved": result["report"]["facts"][0]["cpu_percent"] == 91,
        "expected_conclusion": winner == expected,
        "precommit_before_observation": order_ok and all(s["prediction"] and s["otherwise"] for s in board["steps"]),
        "actual_planner": bool(board["steps"]) and all(s["planner_mode"] == "actual-llm" for s in board["steps"]),
        "budget_and_no_duplicate": 0 < board["used"] <= board["budget"] and len({s["probe_id"] for s in board["steps"]}) == board["used"],
        "scope_preserved": all(c["arguments"]["system_name"] == "payments-service" for c in calls),
        "writer_validation": result["validation"]["passed"],
        "separated_or_withheld": board["stop_code"] == "evidence_separated" if case["winner"] else not result["report"]["recommendations"],
    }
    if case["id"] == "conflict": checks["conflict_visible"] = any(h["status"] == "conflicted" for h in hs)
    if case["id"] == "probe-failure": checks["partial_retained"] = result["status"] == "partial" and any(c["source"] == "diagnostic" for c in result["report"]["failures"])
    return checks


async def evaluate(require_tracing=False, case_ids=None):
    source_fingerprints = fingerprints()
    backend, planner, writer = build_models()
    judge = build_judge()
    client, status = tracing_client(), tracing_status()
    settings = Settings()
    retriever = RunbookIndex(settings.data_dir, settings.data_dir/"runbook_vectors.db", settings.embedding_model)
    await asyncio.to_thread(retriever.prepare)
    await asyncio.to_thread(retriever.search, "CPU 응답 지연")
    folder = ROOT/"artifacts"/"investigation"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder.mkdir(parents=True, exist_ok=False)
    cases = [c for c in CASES if not case_ids or c["id"] in case_ids]
    if not cases: raise ValueError("평가 사례가 없습니다.")
    mcp = MCPClient()
    rows, raw = [], []
    await mcp.start()
    try:
        with TemporaryDirectory() as tmp:
            for case in cases:
                print("실제 가설 조사·Judge: " + case["id"], flush=True)
                store = SqliteSessionStore(Path(tmp)/(case["id"]+".db"))
                recording = RecordingMCP(mcp, case.get("fault_injection", False))
                deps = SupervisorDeps(planner, writer, recording, store, "v2", settings, retriever)
                pc, wc, jc = len(planner.calls), len(writer.calls), len(judge.calls)
                try:
                    with tracing_context(enabled=True if client else "local", client=client, project_name=status["project"],
                                         metadata={"feature": "contrastive-investigation", "data_kind": "synthetic", "case_id": case["id"]}):
                        item = await execute_case(case, deps, judge)
                    checks = check_case(case, item, recording.calls)
                    checks["judge_quality"] = item["judge"]["status"] == "completed" and all(
                        item["judge"]["scores"][key] >= 4 for key in ("groundedness", "numerical_accuracy", "action_conditions", "request_fulfillment", "next_action"))
                    required = {"investigation.choose_question", "investigation.read_evidence", "investigation.test_predictions", "llm.generate", "evaluation.llm_as_judge"}
                    trace = await verify_remote_run(client, item["trace_id"], status["project"], item["judge"].get("scores"), required) if client else {"verified": False, "reason": status["reason"]}
                    board = item["result"]["investigation"]
                    generation = list(planner.calls)[pc:] + list(writer.calls)[wc:]
                    jcals = list(judge.calls)[jc:]
                    outcome = next((h["title"] for h in board["hypotheses"] if h["status"] == "supported"), "근거 상충" if board["stop_code"] == "conflicting_evidence" else "판단 보류")
                    row = {**case, "checks": checks, "passed": all(checks.values()) and item["judge"]["status"] == "completed",
                           "used": board["used"], "sequence": [s["probe"] for s in board["steps"]], "outcome": outcome,
                           "stop_code": board["stop_code"], "elapsed_ms": item["elapsed_ms"], "judge": item["judge"], "trace": trace,
                           "generation_tokens": sum(c["tokens"] for c in generation), "planner_calls": len(list(planner.calls)[pc:]),
                           "judge_tokens": sum(c["tokens"] for c in jcals)}
                    raw.append({"case": case, **item, "trace": trace, "tool_calls": recording.calls,
                                "planner_responses": list(planner.responses)[pc:], "writer_responses": list(writer.responses)[wc:]})
                except Exception as exc:
                    row = {**case, "passed": False, "error": str(exc)[:400], "used": 0, "sequence": [], "outcome": "실행 실패", "trace": {"verified": False}}
                    raw.append({"case": case, "failure": row})
                finally: store.close()
                rows.append(row)
                (folder/"details.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str))
                print(json.dumps({k: row.get(k) for k in ("id", "passed", "used", "outcome", "error", "checks")}, ensure_ascii=False), flush=True)
        control = await negative_control(raw, judge, client, status["project"])
        (folder/"negative_control.json").write_text(json.dumps(control, ensure_ascii=False, indent=2, default=str))
    finally:
        await mcp.stop()
        retriever.close()
        if client: await asyncio.to_thread(client.flush, timeout=15)
    summary = {"created": datetime.now(timezone.utc).isoformat(), "feature": "contrastive-investigation", "mode": "actual-models",
               "planner_model": planner.name, "writer_model": writer.name, "judge_model": judge.name, "case_count": len(rows),
               "passed": sum(r["passed"] for r in rows), "remote_verified": sum(r["trace"].get("verified", False) for r in rows),
               "generation_tokens": sum(r.get("generation_tokens", 0) for r in rows), "judge_tokens": sum(r.get("judge_tokens", 0) for r in rows),
               "negative_control": control, "source_fingerprints": source_fingerprints,
               "source_unchanged": source_fingerprints == fingerprints(),
               "median_generation_ms": statistics.median(r["elapsed_ms"] for r in rows if "elapsed_ms" in r), "cases": rows,
               "details_path": str(folder/"details.json"),
               "limitations": "같은 최초 CPU·경고 로그를 사용하는 고정 합성 사례의 1회 실행입니다. 실제 LLM은 조사 선택·작성·별도 평가에 사용했습니다. 관측 조건에 따른 교차 지지는 실제 원인 확정이 아닙니다. 생성기와 Judge는 같은 Qwen 계열이며 실제 운영 일반화는 검증하지 않았습니다."}
    (folder/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    (ROOT/"artifacts"/"investigation_evaluation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, ensure_ascii=False, indent=2), flush=True)
    if summary["passed"] != len(rows) or not summary["source_unchanged"] or control.get("passed") is False or require_tracing and summary["remote_verified"] != len(rows):
        raise SystemExit("실제 가설 조사 검증 미통과. 결과와 실패 원인을 저장했습니다.")
    return summary


@traceable(name="investigation.false_cause_control", process_inputs=lambda v: {"fault": "invented definitive batch cause despite contrary evidence"})
async def score_false_cause(result, judge):
    judged = await judge_report(result, judge)
    rt = get_current_run_tree()
    return judged, str(rt.id) if rt else None


async def negative_control(raw, judge, client, project):
    candidate = next((r for r in raw if r["case"]["id"] == "traffic" and "result" in r), None)
    if not candidate:
        return {"status": "skipped", "reason": "요청량 사례가 선택되지 않았습니다."}
    wrong = copy.deepcopy(candidate["result"])
    wrong["final"] += "\n최종 확정 결론: 중복 배치 작업이 CPU 상승의 원인으로 확정되었습니다. 반증 관측은 무시해도 되며 추가 확인이 필요 없습니다."
    with tracing_context(enabled=True if client else "local", client=client, project_name=project):
        judged, run_id = await score_false_cause(wrong, judge)
    trace = await verify_remote_run(client, run_id, project, judged.get("scores"), {"evaluation.llm_as_judge", "llm.generate"}) if client else {"verified": False}
    good = candidate["judge"]["scores"]["groundedness"]
    bad = (judged.get("scores") or {}).get("groundedness")
    return {"status": judged["status"], "passed": bad is not None and bad < good and bad <= 2,
            "correct_score": good, "corrupted_score": bad, "judge": judged, "trace": trace,
            "injection": "원본 CPU 91%와 관측은 유지하고, 반증된 중복 배치를 원인 확정하는 문장만 최종 답변에 추가함"}


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--require-tracing", action="store_true")
    cli.add_argument("--case", action="append")
    args = cli.parse_args()
    asyncio.run(evaluate(args.require_tracing, args.case))
