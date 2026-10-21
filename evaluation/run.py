"""Reproducible original-v2 vs improved-v2 evaluation. No external generation by default.
Run: .venv/bin/python -m evaluation.run [--judge --backend ollama|openai]
The explicit --judge option makes a real, potentially billed model call.
"""
import argparse
import asyncio
import importlib.util
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

# Evaluation remains local unless tracing is explicitly enabled by its own caller.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.graph import build_graph
from agent.session_store import SqliteSessionStore
from agent.settings import Settings, ROOT
from agent.retrieval import RunbookIndex
from agent.reporting import default_selection
from agent.judge import judge_report
from tests.support import FixtureMCP

spec = importlib.util.spec_from_file_location("agent.baseline_graph", ROOT / "artifacts/baseline/graph_v2.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

CASES = [
    {"id":"ambiguous","label":"대상 없는 장애 질문", "query":"로그인 장애를 진단해주세요", "targets":[], "clarify":True},
    {"id":"unknown","label":"미등록 시스템 자동 대체 방지", "query":"billing-service 장애 진단", "targets":[], "clarify":True},
    {"id":"two-targets","label":"명시한 두 시스템 모두 조사", "query":"gateway-service와 payments-service 장애 진단", "targets":["gateway-service","payments-service"], "runbooks":["network-timeout","cpu-spike"]},
    {"id":"cpu","label":"CPU 급증과 근거 수치 일치", "query":"payments-service CPU 급증 진단", "targets":["payments-service"], "runbooks":["cpu-spike"]},
    {"id":"paraphrase","label":"우회 표현으로 메모리 문서 검색", "query":"cache-service에서 쓰고 난 공간이 반환되지 않고 계속 차오릅니다. 진단해주세요", "targets":["cache-service"], "runbooks":["memory-leak"]},
    {"id":"partial","label":"일부 조회 시간 초과와 성공 결과 유지", "query":"payments-service와 web-01 장애 진단", "targets":["payments-service","web-01"], "fail":True, "runbooks":["cpu-spike"]},
    {"id":"bad-draft","label":"CPU 39% 오류 초안 차단", "query":"payments-service CPU 급증 진단", "targets":["payments-service"], "wrong":True},
    {"id":"resume","label":"되묻기 후 원래 증상으로 조사", "query":"payments-service", "targets":["payments-service"], "resume":True},
    {"id":"stable","label":"배포 전후 정상 유지", "query":"web-01 배포 전후 점검 진단", "targets":["web-01"], "scenario":"stable", "verdict":"정상"},
    {"id":"cpu-rise","label":"배포 전후 CPU +57%p", "query":"web-01 배포 전후 점검 진단", "targets":["web-01"], "scenario":"cpu-rise", "verdict":"주의"},
    {"id":"new-alert","label":"수치가 같아도 새 알림 발생 감지", "query":"web-01 배포 전후 점검 진단", "targets":["web-01"], "scenario":"new-alert", "verdict":"주의"},
    {"id":"missing-after","label":"배포 후 샘플 누락은 정보 부족", "query":"web-01 배포 전후 점검 진단", "targets":["web-01"], "scenario":"missing-after", "verdict":"정보 부족"},
]


class AdversarialWriter(QualityLLM):
    async def select_report(self, report, feedback):
        d = default_selection(report)
        d["facts"][0]["cpu_percent"] = 39
        return d, {"usd":0, "tokens":0}
    async def write(self, query, collected, attempt, feedback, on_token=None):
        return "1) payments-service 상태=degraded, CPU 39% 입니다. 2) 원인을 확인하세요.", {"usd":0,"tokens":0}


def score(case, result, calls):
    observed = {a["system_name"] for name,a in calls if name in ("get_monitoring_status", "get_deployment_snapshot")}
    expected = set(case["targets"])
    # Unknown/missing scope must issue no monitoring/log calls.
    scope = observed == expected if not case.get("clarify") else not calls and result.get("route") == "clarify"
    failures = result.get("report", {}).get("failures", [])
    if case.get("fail"):
        handling = result.get("status") == "partial" and bool(failures) and "CPU 91.0%" in result.get("final", "")
    else:
        handling = "error" not in result
    passed = scope and handling
    if case.get("wrong"):
        passed = passed and result.get("status") == "validation_failed" and "CPU 39" not in result.get("final", "") and "CPU 91.0%" in result.get("final", "")
    if case.get("resume"):
        passed = passed and "갑자기" in result.get("effective_query", "")
    if case.get("scenario"):
        comp = result.get("report", {}).get("comparisons", [])
        passed = passed and bool(comp) and comp[0]["verdict"] == case["verdict"]
        if case["scenario"] == "cpu-rise":
            passed = passed and comp[0]["deltas"].get("cpu_pp") == 57.0
    documents = {c.get("data",{}).get("id","")[2:] for c in result.get("collected",[]) if c.get("source")=="runbook" and isinstance(c.get("data"),dict)}
    if not documents:
        documents = {e.get("target") for e in result.get("events",[]) if e.get("type")=="TaskCompleted" and e.get("source")=="runbook"}
    recall = len(documents & set(case["runbooks"])) / len(case["runbooks"]) if case.get("runbooks") else None
    # Independently parse CPU claims in the delivered text, rather than grading our validator flag.
    import re
    claims = re.findall(r"([a-z][a-z0-9-]+)\s*(?:\([^)]*\))?\s*(?:상태=|:)?.{0,45}?CPU\s+(\d+(?:\.\d+)?)%", result.get("final", ""))
    facts = [c["data"] for c in result.get("collected",[]) if c.get("source") in ("monitoring","snapshot") and isinstance(c.get("data"),dict)]
    supported = sum(any(d.get("system_name")==s and d.get("cpu_percent")==float(n) for d in facts) for s,n in claims)
    numbers = supported / len(claims) if claims else None
    return {"passed": bool(passed), "scope_exact": scope, "failure_handling": handling, "runbook_recall": recall,
            "numeric_accuracy": numbers, "numeric_claims": len(claims), "numeric_supported": supported,
            "documents": sorted(documents), "observed_targets": sorted(observed),
            "status": result.get("status", "legacy"), "validation_attempts": result.get("validation_attempts",0)}


async def run(judge=False, backend="ollama"):
    settings=Settings()
    retriever=RunbookIndex(settings.data_dir, settings.data_dir/'runbook_vectors.db', settings.embedding_model)
    cold=time.perf_counter();await asyncio.to_thread(retriever.prepare)
    # Load encoder once to exclude first-use download/model initialization from warm latency.
    await asyncio.to_thread(retriever.search,"운영 장애 진단")
    warmup_ms=round((time.perf_counter()-cold)*1000,2)
    rows=[];raw=[]
    judge_llm=None
    if judge:
        from agent.llm_runtime import build_judge
        judge_llm=build_judge(backend)
    with TemporaryDirectory() as tmp:
        for case in CASES:
            variants={};rawcase={"case":case}
            for name,builder in (("before",baseline.build_graph),("after",build_graph)):
                mcp=FixtureMCP({('get_monitoring_status','web-01')} if case.get('fail') else set())
                store=SqliteSessionStore(Path(tmp)/(case['id']+name+'.db'))
                quality=AdversarialWriter('adversarial',0) if case.get('wrong') else QualityLLM('fixed-fake',0.005)
                deps=SupervisorDeps(FastLLM('fixed-fake',0.00015),quality,mcp,store,'v2',Settings(tool_timeout=.2),retriever)
                state={"query":case['query'],"thread_id":"evaluation","history":[],"events":[],"cost_usd":0,
                       "context":{},"mode":"deployment" if 'scenario' in case else "helpdesk", "scenario":case.get('scenario','stable'),
                       "details":{"onset":"2026-10-21T09:00:00+09:00","error_message":"없음"}}
                if case.get('resume') and name=='after':
                    state['context']={"pending":{"query":"CPU가 갑자기 올라가고 응답이 느려요. 진단해주세요","mode":"helpdesk"}}
                start=time.perf_counter()
                try:result=await builder(deps).ainvoke(state)
                except Exception as exc:result={"error":str(exc),"final":""}
                elapsed=round((time.perf_counter()-start)*1000,2)
                measurement=score(case,result,mcp.calls)
                measurement['elapsed_ms']=elapsed
                if judge and name=='after':measurement['judge']=await judge_report(result,judge_llm)
                variants[name]=measurement;rawcase[name]={"result":result,"tool_calls":mcp.calls,"measurement":measurement}
                store.close()
            rows.append({"id":case['id'],"label":case['label'],**variants});raw.append(rawcase)
    def rate(name,key):return sum(r[name][key] for r in rows)/len(rows)*100
    def recall(name):
        values=[r[name]['runbook_recall'] for r in rows if r[name]['runbook_recall'] is not None]
        return sum(values)/len(values)*100
    def numbers(name):
        n=sum(r[name]['numeric_claims'] for r in rows)
        return sum(r[name]['numeric_supported'] for r in rows)/n*100 if n else 0
    metrics=[
        {"label":"시나리오 통과율", "before":f"{rate('before','passed'):.1f}%", "after":f"{rate('after','passed'):.1f}%"},
        {"label":"조사 대상 정확 일치율", "before":f"{rate('before','scope_exact'):.1f}%", "after":f"{rate('after','scope_exact'):.1f}%"},
        {"label":"필수 Runbook 검색 재현율", "before":f"{recall('before'):.1f}%", "after":f"{recall('after'):.1f}%"},
        {"label":"CPU 수치 근거 일치율", "before":f"{numbers('before'):.1f}%", "after":f"{numbers('after'):.1f}%"},
        {"label":"처리 시간 중앙값 (warm)", "before":f"{statistics.median(r['before']['elapsed_ms'] for r in rows):.1f} ms", "after":f"{statistics.median(r['after']['elapsed_ms'] for r in rows):.1f} ms"},
        {"label":"실제 생성 LLM / Judge", "before":"사용 안 함 / 사용 안 함", "after":f"사용 안 함 / {'실행' if judge else '미실행'}"}]
    report={"created":datetime.now(timezone.utc).isoformat(),"description":f"원본 v2 보존본과 현재 개선 그래프 · 고정 시나리오 {len(rows)}개 · 생성 모델은 fake · 실제 로컬 다국어 임베딩 사용",
            "metrics":metrics,"cases":rows,"warmup_ms":warmup_ms,
            "limitations":"소규모 교육용 데이터 1회 평가입니다. 원본의 태스크당 350ms 인위적 지연 제거가 시간 차이에 포함됩니다. 실모델 품질·운영 SLA·토큰 비용을 증명하지 않습니다. CPU 수치 평가는 최종 답변의 CPU 주장만 대상으로 합니다. LLM Judge는 명시적으로 실행할 때만 점수를 저장합니다."}
    (ROOT/'artifacts/evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'artifacts/evaluation_details.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2,default=str)+'\n')
    retriever.close()
    print(json.dumps(report['metrics'],ensure_ascii=False,indent=2))
    failed=[r['id'] for r in rows if not r['after']['passed']]
    if failed:raise SystemExit('개선 버전 미통과: '+','.join(failed))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--judge',action='store_true');parser.add_argument('--backend',choices=['ollama','openai'],default='ollama')
    args=parser.parse_args();asyncio.run(run(args.judge,args.backend))
