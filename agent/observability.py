"""Tracing configuration with legacy aliases and explicit remote read-back verification."""
import asyncio
import os
from langsmith import Client


def tracing_status():
    key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or ""
    requested = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false")).lower() == "true"
    configured = bool(requested and key and not key.endswith("..."))
    return {"requested": requested, "configured": configured,
            "project": os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or "capstone-all-total-live",
            "endpoint": os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT") or "https://api.smith.langchain.com",
            "reason": None if configured else ("LANGSMITH_API_KEY 미설정" if not key or key.endswith("...") else "tracing 비활성화")}


def tracing_client():
    state = tracing_status()
    if not state["configured"]:
        return None
    return Client(api_url=state["endpoint"], api_key=os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"), timeout_ms=10000)


def normalize_tracing_env():
    # Avoid repeated SDK failures when a requested remote connection has no credentials.
    state = tracing_status()
    os.environ["LANGSMITH_TRACING"] = "true" if state["configured"] else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = os.environ["LANGSMITH_TRACING"]
    if state["configured"]:
        os.environ["LANGSMITH_PROJECT"] = state["project"]
    return state


async def verify_remote_run(client, run_id, project, scores=None, required_spans=None):
    if client is None:
        return {"status": "blocked", "verified": False, "reason": "LangSmith API 키가 없어 원격 저장 확인 불가"}
    await asyncio.to_thread(client.flush, timeout=15)
    remote = None
    for attempt in range(3):
        try:
            remote = await asyncio.to_thread(client.read_run, run_id, load_child_runs=True)
            if remote.end_time:
                break
        except Exception as exc:
            if attempt == 2:
                return {"status": "failed", "verified": False, "reason": f"원격 조회 실패 ({type(exc).__name__})"}
        await asyncio.sleep(attempt + 1)
    if remote is None:
        return {"status": "failed", "verified": False, "reason": "원격 실행 미조회"}
    def flatten(run):
        return [run] + [sub for c in (run.child_runs or []) for sub in flatten(c)]
    runs = flatten(remote)
    llm_runs = [r for r in runs if r.run_type == "llm"]
    token_runs = [r for r in llm_runs if (r.outputs or {}).get("usage_metadata", {}).get("total_tokens", 0) > 0]
    feedback = []
    try:
        for key, score in (scores or {}).items():
            if isinstance(score, int):
                item = await asyncio.to_thread(client.create_feedback, run_id, key="live_"+key,
                                               score=score/5, comment="Actual LLM Judge; scale normalized from 0–5",
                                               session_id=str(remote.session_id),
                                               stop_after_attempt=2)
                feedback.append(str(item.id))
        saved_feedback = await asyncio.to_thread(lambda: list(client.list_feedback(run_ids=[run_id]))) if feedback else []
        feedback_verified = not feedback or set(feedback).issubset({str(f.id) for f in saved_feedback})
        url = await asyncio.to_thread(client.get_run_url, run=remote, project_name=project)
    except Exception as exc:
        return {"status": "failed", "verified": False, "reason": f"원격 피드백 검증 실패 ({type(exc).__name__})", "run_id": str(run_id)}
    required = set(required_spans) if required_spans is not None else {"metrics_specialist.collect", "logs_specialist.collect", "runbook_specialist.retrieve", "llm.generate", "evaluation.llm_as_judge"}
    names = {r.name for r in runs}
    verified = bool(remote.end_time and not remote.error and token_runs and required.issubset(names) and feedback_verified)
    return {"status": "verified" if verified else "incomplete", "verified": verified, "run_id": str(run_id),
            "url": url, "project": project, "span_count": len(runs), "llm_spans": len(llm_runs),
            "llm_spans_with_tokens": len(token_runs), "span_names": sorted(names),
            "missing_spans": sorted(required-names), "feedback_ids": feedback, "feedback_verified": feedback_verified,
            "ended": bool(remote.end_time), "error": remote.error}
