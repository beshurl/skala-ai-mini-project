"""Actual same-origin SSE/JSON → MCP/LLM → SQLite and remote trace verification."""
import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from dotenv import load_dotenv
load_dotenv()
from agent.observability import tracing_client, tracing_status, verify_remote_run
from agent.settings import ROOT


async def main():
    url = os.getenv("INVESTIGATION_URL", "http://127.0.0.1:8600")
    thread = "investigation-smoke-" + str(uuid4())
    checks, results = {}, []
    remote = tracing_client()
    async with httpx.AsyncClient(base_url=url, timeout=190) as client:
        health = (await client.get('/health')).json()
        assert health['llm_backend'] in ('ollama','openai')
        checks['actual_backend'] = True
        body = {'message':'payments-service CPU가 급증하고 중복 배치 경고가 있습니다. 다른 가설과 구별해주세요.',
                'thread_id':thread, 'targets':['payments-service'], 'evidence_case':'traffic',
                'details':{'onset':'2026-10-21 09:00~09:05','error_message':'응답 지연'}}
        events = []
        async with client.stream('POST','/chat/stream',json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith('data: '): continue
                value = line[6:]
                if value == '[DONE]': checks['done_marker'] = True
                else: events.append(json.loads(value))
        finals = [e for e in events if e['type']=='FinalAnswer']
        assert len(finals)==1 and not any(e['type']=='AnswerToken' for e in events)
        final=finals[0]
        assert final['validation']['passed']
        board=final['report']['investigation']
        assert [h['kind'] for h in board['hypotheses'] if h['status']=='supported']==['traffic']
        assert any(e['type']=='ProbePlanned' for e in events)
        assert any(e['type']=='HypothesesUpdated' for e in events)
        assert final['metadata']['tokens']>0 and all(s['planner_mode']=='actual-llm' for s in board['steps'])
        checks['sse_actual_plan_and_single_final']=True
        saved=(await client.get('/sessions/'+thread)).json()
        assert saved['records'][0]['result']['investigation']==board
        assert saved['records'][0]['result']['evidence_case']=='traffic'
        checks['sqlite_board_restore']=True
        results.append({'transport':'SSE','final':final})
        second=await client.post('/chat',json={**body,'thread_id':thread+'-conflict','evidence_case':'conflict'})
        second.raise_for_status()
        conflict=second.json()
        assert conflict['report']['investigation']['stop_code']=='conflicting_evidence'
        assert conflict['report']['facts'][0]['cpu_percent']==91
        assert not conflict['report']['recommendations']
        checks['json_conflict_withholds_actions']=True
        results.append({'transport':'JSON','final':conflict})
        other=(await client.get('/sessions/'+thread+'-unrelated')).json()
        assert other['messages']==[]
        checks['session_isolation']=True
        for row in results:
            run_id=row['final']['metadata']['langsmith_run_id']
            row['trace']=await verify_remote_run(remote,run_id,tracing_status()['project'],required_spans={
                'investigation.choose_question','investigation.read_evidence','investigation.test_predictions','llm.generate'})
        checks['remote_traces']=all(r['trace']['verified'] for r in results)
    summary={'created':datetime.now(timezone.utc).isoformat(),'base_url':url,'thread_id':thread,'checks':checks,
             'passed':all(checks.values()),'results':results,'data_kind':'synthetic-observations; actual-models'}
    (ROOT/'artifacts/investigation_api_smoke.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':summary['passed'],'checks':checks,'thread_id':thread},ensure_ascii=False))
    if not summary['passed']: raise SystemExit('통합 검증 미통과')


if __name__=='__main__':asyncio.run(main())
