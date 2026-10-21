"""Actual generation + separate actual Judge + real MCP + optional verified LangSmith.

python -m evaluation.live --backend ollama [--case cpu] [--require-tracing]
Synthetic monitoring inputs are retained; real model calls are never replaced by fake.
"""
import argparse
import asyncio
import copy
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()

from langsmith import traceable, tracing_context
from langsmith.run_helpers import get_current_run_tree
from agent.deps import SupervisorDeps
from agent.settings import Settings, ROOT
from agent.graph import build_graph
from agent.session_store import SqliteSessionStore
from agent.mcp_client import MCPClient
from agent.retrieval import RunbookIndex
from agent.llm_runtime import build_models, build_judge
from agent.judge import judge_report
from agent.reporting import write_selection
from agent.observability import tracing_status, tracing_client, verify_remote_run
# Import the fixed evaluation definitions only; importing them disables no tracing in this scope.
from evaluation.run import CASES, score


class TrackingMCP:
    def __init__(self, client, fail=False):
        self.client, self.fail, self.calls = client, fail, []
    async def call_tool(self, name, arguments, **kwargs):
        self.calls.append((name, dict(arguments)))
        if self.fail and name == 'get_monitoring_status' and arguments['system_name'] == 'web-01':
            raise TimeoutError('explicit evaluation failure injection')
        return await self.client.call_tool(name, arguments, **kwargs)
    def __getattr__(self, key):
        return getattr(self.client, key)


class CorruptAfterRealGeneration:
    def __init__(self, model):
        self.model = model
        self.name = model.name + ':fault-injection'
    async def select_report(self, report, feedback):
        draft, usage = await write_selection(self.model, report, feedback)
        if draft.get('facts'):
            draft['facts'][0]['cpu_percent'] = 39
        return draft, usage


@traceable(name='live_evaluation_case', process_inputs=lambda v: {'case': v['case']})
async def execute_case(case, deps, judge):
    state = {'query': case['query'], 'thread_id': 'live-evaluation', 'history': [], 'events': [], 'cost_usd': 0,
             'context': {}, 'mode': 'deployment' if 'scenario' in case else 'helpdesk',
             'scenario': case.get('scenario', 'stable'), 'details': {'onset': '2026-10-21 오전 9시', 'error_message': '없음'}}
    graph = build_graph(deps)
    if case.get('resume'):
        first = await graph.ainvoke({**state, 'query': 'CPU가 갑자기 올라가고 응답이 느려요. 진단해주세요'})
        state['context'] = first['context']
    started = time.perf_counter()
    result = await graph.ainvoke(state)
    generation_ms = round((time.perf_counter()-started)*1000, 2)
    judged = await judge_report(result, judge)
    rt = get_current_run_tree()
    return {'result': result, 'judge': judged, 'generation_ms': generation_ms,
            'trace_id': str(rt.id) if rt else None}


async def evaluate(backend='ollama', case_ids=None, require_tracing=False):
    status = tracing_status()
    client = tracing_client()
    project = status['project']
    backend, fast, writer = build_models(backend)
    judge = build_judge(os.getenv('JUDGE_BACKEND', backend))
    settings = Settings()
    retriever = RunbookIndex(settings.data_dir, settings.data_dir/'runbook_vectors.db', settings.embedding_model)
    await asyncio.to_thread(retriever.prepare)
    await asyncio.to_thread(retriever.search, '운영 장애 진단')
    selected = [c for c in CASES if not case_ids or c['id'] in case_ids]
    if not selected:
        raise ValueError('선택한 평가 사례가 없습니다.')
    run_label = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT/'artifacts'/'live'/run_label
    folder.mkdir(parents=True, exist_ok=False)
    rows, raw = [], []
    mcp = MCPClient()
    try:
        await mcp.start()
        with TemporaryDirectory() as tmp:
            for case in selected:
                print('실제 생성·평가: '+case['id'], flush=True)
                store = SqliteSessionStore(Path(tmp)/(case['id']+'.db'))
                tracking = TrackingMCP(mcp, case.get('fail', False))
                quality = CorruptAfterRealGeneration(writer) if case.get('wrong') else writer
                deps = SupervisorDeps(fast, quality, tracking, store, 'v2', settings, retriever)
                wcount, jcount = len(writer.calls), len(judge.calls)
                try:
                    with tracing_context(enabled=True if client else 'local', client=client, project_name=project,
                                         metadata={'evaluation_mode': 'actual-models', 'case_id': case['id'], 'data_kind': 'synthetic'}):
                        item = await execute_case(case, deps, judge, langsmith_extra={'run_id': str(uuid4())})
                    measured = score(case, item['result'], tracking.calls)
                    measured['elapsed_ms'] = item['generation_ms']
                    measured['judge'] = item['judge']
                    calls = list(writer.calls)[wcount:]
                    jcalls = list(judge.calls)[jcount:]
                    measured['generation_calls'] = len(calls)
                    measured['generation_tokens'] = sum(c['tokens'] for c in calls)
                    measured['judge_tokens'] = sum(c['tokens'] for c in jcalls)
                    measured['generation_input_tokens'] = sum(c['input_tokens'] for c in calls)
                    measured['generation_output_tokens'] = sum(c['output_tokens'] for c in calls)
                    measured['judge_elapsed_ms'] = sum(c['elapsed_ms'] for c in jcalls)
                    if client:
                        required = {'llm.generate', 'evaluation.llm_as_judge'}
                        if item['result'].get('route') != 'clarify':
                            required.update({'metrics_specialist.collect', 'logs_specialist.collect', 'runbook_specialist.retrieve'})
                        item['remote_trace'] = await verify_remote_run(client, item['trace_id'], project,
                                                                     item['judge'].get('scores'), required)
                    else:
                        item['remote_trace'] = {'status': 'blocked', 'verified': False, 'reason': status['reason'],
                                                'local_trace_id': item['trace_id']}
                    row = {'id': case['id'], 'label': case['label'], 'fault_injection': bool(case.get('wrong') or case.get('fail')),
                           **measured, 'trace': item['remote_trace']}
                    raw.append({'case': case, **item, 'tool_calls': tracking.calls,
                                'generation_responses': list(writer.responses)[wcount:],
                                'judge_responses': list(judge.responses)[jcount:]})
                except Exception as exc:
                    row = {'id': case['id'], 'label': case['label'], 'passed': False, 'error': str(exc)[:300],
                           'judge': {'status': 'failed', 'scores': None}, 'trace': {'verified': False}}
                    raw.append({'case': case, 'failure': row})
                finally:
                    store.close()
                rows.append(row)
                (folder/'details.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str)+'\n')
                print(json.dumps({k: row.get(k) for k in ('id','passed','generation_tokens','judge_tokens')}, ensure_ascii=False), flush=True)
        control = await negative_control(raw, judge, client, project)
    finally:
        await mcp.stop()
        retriever.close()
        if client:
            await asyncio.to_thread(client.flush, timeout=15)
    dimensions = ['groundedness','numerical_accuracy','action_conditions','request_fulfillment','next_action']
    completed = [r for r in rows if r.get('judge',{}).get('status') == 'completed']
    averages = {key: round(statistics.mean(r['judge']['scores'][key] for r in completed), 3) if completed else None for key in dimensions}
    remote_verified = sum(r.get('trace',{}).get('verified',False) for r in rows)
    summary = {'created': datetime.now(timezone.utc).isoformat(), 'mode': 'actual-generation-and-actual-judge',
               'data_kind': 'synthetic-monitoring-and-logs', 'generation_model': writer.name, 'judge_model': judge.name,
               'case_count': len(rows), 'passed': sum(r['passed'] for r in rows), 'judge_completed': len(completed),
               'judge_mean_scores': averages, 'negative_control': control,
               'generation_tokens': sum(r.get('generation_tokens',0) for r in rows),
               'judge_tokens': sum(r.get('judge_tokens',0) for r in rows),
               'negative_control_tokens': control.get('judge', {}).get('usage', {}).get('tokens', 0),
               'total_tokens': sum(r.get('generation_tokens',0)+r.get('judge_tokens',0) for r in rows)+control.get('judge', {}).get('usage', {}).get('tokens',0),
               'median_generation_ms': round(statistics.median(r['elapsed_ms'] for r in rows if 'elapsed_ms' in r),2),
               'tracing': {**status, 'remote_verified_cases': remote_verified,
                           'verified': bool(remote_verified == len(rows) and client)}, 'cases': rows,
               'api_cost_usd': 0 if backend == 'ollama' and judge.provider == 'ollama' else None,
               'cost_limit': 'Local hardware/electricity cost is not included. No fabricated provider price.',
               'limitations': '고정 합성 데이터의 단일 실행이며 실제 운영 정확도나 모델 전반의 성능을 뜻하지 않습니다. 같은 Qwen 계열 생성기와 Judge의 상관 편향이 있을 수 있습니다. fault-injection 사례는 실제 모델 출력에 의도적으로 오류를 주입했습니다.'}
    (folder/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'artifacts'/'live_evaluation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    (ROOT/'artifacts'/'live_latest.json').write_text(json.dumps({'summary':str(folder/'summary.json'),'details':str(folder/'details.json')},indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'},ensure_ascii=False,indent=2),flush=True)
    if require_tracing and not summary['tracing']['verified']:
        raise SystemExit('LangSmith 원격 검증 미완료. 실제 모델 결과는 저장했습니다.')
    if summary['passed'] != len(rows) or len(completed) != len(rows) or control.get('passed') is False:
        raise SystemExit('실제 평가 미통과 항목이 있습니다. 저장된 결과를 확인하세요.')
    return summary


@traceable(name='judge_negative_control', process_inputs=lambda v: {'result':v['result']})
async def score_negative(result, judge):
    return await judge_report(result, judge)


async def negative_control(raw, judge, client, project):
    candidate = next((r for r in raw if r.get('case',{}).get('id')=='cpu' and r.get('judge',{}).get('scores')), None)
    if not candidate:
        return {'status':'skipped','reason':'CPU 정상 생성 사례가 선택되지 않았습니다.'}
    wrong = copy.deepcopy(candidate['result'])
    original = wrong['final']
    wrong['final'] = original.replace('CPU 91.0%', 'CPU 39.0%')
    if wrong['final'] == original:
        return {'status':'failed','passed':False,'reason':'수치 오류 대조군을 구성하지 못했습니다.'}
    wrong['validation'] = {'passed':True}
    with tracing_context(enabled=True if client else 'local', client=client, project_name=project):
        judged = await score_negative(wrong, judge)
    good = candidate['judge']['scores']['numerical_accuracy']
    bad = (judged.get('scores') or {}).get('numerical_accuracy')
    return {'status':judged['status'],'passed':bad is not None and bad < good and bad <= 2,
            'correct_answer_score':good,'corrupted_answer_score':bad,'judge':judged,
            'injection':'최종 답변만 CPU 91% → 39%로 바꾸고 검증 통과 플래그를 유지함'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend',choices=['ollama','openai'],default=os.getenv('LLM_BACKEND','ollama'))
    parser.add_argument('--case',action='append',dest='case_ids')
    parser.add_argument('--require-tracing',action='store_true')
    args=parser.parse_args()
    asyncio.run(evaluate(args.backend,args.case_ids,args.require_tracing))
