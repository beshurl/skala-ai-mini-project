import json
import pytest
from fastapi.testclient import TestClient
import server
from agent.settings import Settings
from tests.support import FixtureMCP, FixedRetriever


class LocalMCP(FixtureMCP):
    async def start(self):pass
    async def stop(self):pass


class LocalIndex(FixedRetriever):
    def __init__(self,*args):pass
    def close(self):pass


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "MCPClient", LocalMCP)
    monkeypatch.setattr(server, "RunbookIndex", LocalIndex)
    monkeypatch.setattr(server, "Settings", lambda: Settings(db_path=tmp_path/'api.db',tool_timeout=.1))
    monkeypatch.setenv("LLM_BACKEND","fake")
    with TestClient(server.app) as c:yield c


def test_api_input_validation(client):
    assert client.post('/chat',json={'message':'   '}).status_code == 422
    assert client.post('/chat',json={'message':'x'*6001}).status_code == 422
    assert client.post('/chat',json={'message':'진단','thread_id':'../../bad'}).status_code == 422
    assert client.post('/chat',json={'message':'진단','mode':'shell'}).status_code == 422


def test_json_sse_share_persistence_and_opaque_sessions(client):
    body={'message':'payments-service CPU 급증 진단','thread_id':'opaque-a'}
    result=client.post('/chat',json=body).json()
    assert result['report']['facts'][0]['cpu_percent']==91
    assert result['validation']['passed']
    stream=client.post('/chat/stream',json={**body,'thread_id':'opaque-b'})
    blocks=[b[6:] for b in stream.text.strip().split('\n\n')]
    assert blocks[-1]=='[DONE]'
    events=[json.loads(b) for b in blocks[:-1]]
    assert len([e for e in events if e['type']=='FinalAnswer'])==1
    assert not any(e['type']=='AnswerToken' for e in events)
    final=next(e for e in events if e['type']=='FinalAnswer')
    assert final['report']==result['report']
    session=client.get('/sessions/opaque-b').json()
    assert len(session['messages'])==2 and len(session['records'])==1
    assert session['records'][0]['result']['validation']['passed']
    assert client.get('/sessions/unrelated').json()['messages']==[]
    assert client.get('/sessions/opaque-b').json()['records'][0]['result']['events']


def test_sse_clarification_persists_and_continues(client):
    first=client.post('/chat/stream',json={'message':'로그인 장애를 진단해주세요','thread_id':'clarify'}).text
    assert '대상' in first
    assert client.get('/sessions/clarify').json()['context']['pending']
    second=client.post('/chat',json={'message':'auth-service','thread_id':'clarify'}).json()
    assert second['metadata']['targets']==['auth-service']
    assert '로그인 장애' in second['report']['question']


def test_retry_scope_and_cross_session_record_rejected(client):
    first=client.post('/chat',json={'message':'payments-service 장애 진단','thread_id':'a'}).json()
    record=first['metadata']['record_id']
    bad=client.post('/chat',json={'message':'payments-service 장애 진단','thread_id':'b','targets':['payments-service'],'retry_record_id':record})
    assert bad.status_code==409
    changed=client.post('/chat',json={'message':'payments-service 장애 진단','thread_id':'a','targets':['web-01'],'retry_record_id':record})
    assert changed.status_code==409


def test_request_timeout_keeps_already_completed_observations(client):
    import asyncio
    from dataclasses import replace
    deps=server.app.state.deps
    deps.settings=replace(deps.settings,request_timeout=.08,tool_timeout=1)
    original=deps.mcp.call_tool
    async def slow(name,args):
        if name=='get_monitoring_status' and args['system_name']=='payments-service':
            await asyncio.sleep(.3)
        return await original(name,args)
    deps.mcp.call_tool=slow
    response=client.post('/chat',json={'message':'auth-service와 payments-service 장애 진단','thread_id':'timeout'})
    result=response.json()
    assert result['metadata']['status']=='failed'
    assert any(f['system_name']=='auth-service' for f in result['report']['facts'])
    assert not result['validation']['passed']
    assert not result['report']['recommendations']
    assert '초과' in result['reply']


def test_api_restores_board_and_forbids_changing_retry_dataset(client):
    body = {"message": "payments-service CPU 급증 진단", "thread_id": "investigation", "evidence_case": "traffic"}
    result = client.post('/chat', json=body).json()
    saved = client.get('/sessions/investigation').json()['records'][0]
    assert saved['result']['investigation'] == result['report']['investigation']
    bad = client.post('/chat', json={**body, "evidence_case": "batch", "targets": ["payments-service"],
                                    "retry_record_id": saved['id']})
    assert bad.status_code == 409


def test_identical_replies_keep_distinct_message_record_ids(client):
    body={'message':'web-01 상태 진단','thread_id':'same-reply'}
    first=client.post('/chat',json=body).json()
    second=client.post('/chat',json=body).json()
    assert first['reply']==second['reply']
    messages=client.get('/sessions/same-reply').json()['messages']
    ids=[m['record_id'] for m in messages if m['role']=='assistant']
    assert ids==[first['metadata']['record_id'],second['metadata']['record_id']]


def test_followup_to_older_record_restores_original_scope_and_symptoms(client):
    first=client.post('/chat',json={'message':'payments-service CPU 급증 진단','thread_id':'older',
                     'details':{'onset':'오전 9시','error_message':'응답 지연'}}).json()
    client.post('/chat',json={'message':'gateway-service 504 장애 진단','thread_id':'older'})
    record=first['metadata']['record_id']
    resumed=client.post('/chat',json={'message':'그럼 다시 확인해주세요','thread_id':'older',
                       'targets':['payments-service'],'context_record_id':record}).json()
    assert resumed['report']['targets']==['payments-service']
    assert 'CPU 급증' in resumed['report']['question']
    assert client.get('/sessions/older').json()['records'][0]['result']['details']['onset']=='오전 9시'
    assert client.post('/chat',json={'message':'그럼 다시 확인','thread_id':'another',
                       'context_record_id':record}).status_code==409


@pytest.mark.parametrize("transport", ["json", "post-sse", "get-sse"])
@pytest.mark.parametrize("message", ["ㅋㅋㅋㅋ", "😀😀😀", "asdf qwer", "오늘 날씨 알려줘", "안녕", "네", "CPU로 시 써줘"])
def test_rejected_input_never_enters_graph_or_conversation_memory(client, transport, message):
    class NoExecution:
        calls = 0
        def astream(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("Rejected input reached the model/tool graph")
    graph = NoExecution()
    server.app.state.graph = graph
    body = {"message": message, "thread_id": "no-spend", "targets": ["payments-service"]}
    if transport == "json":
        response = client.post('/chat', json=body)
        result = response.json()
    else:
        response = (client.post('/chat/stream', json=body) if transport == "post-sse" else
                    client.get('/chat/stream', params={"message": message, "thread_id": "no-spend"}))
        blocks = [b[6:] for b in response.text.strip().split('\n\n')]
        assert blocks[-1] == '[DONE]'
        events = [json.loads(b) for b in blocks[:-1]]
        assert [e['type'] for e in events] == ['InputRejected', 'FinalAnswer']
        result = events[-1]
    assert response.status_code == 200
    assert result['metadata']['status'] == 'rejected'
    assert result['metadata']['tokens'] == 0 and result['metadata']['model_usage'] == []
    assert result['metadata']['llm_called'] is False and result['metadata']['record_id'] is None
    assert not result['input_validation']['passed'] and '사용 토큰: 0' in result['reply']
    assert graph.calls == 0 and server.app.state.deps.mcp.calls == []
    assert client.get('/sessions/no-spend').json() == {'messages': [], 'records': [], 'context': {}}


def test_rejection_preserves_pending_question_and_accepts_short_target_reply(client):
    body = {'thread_id': 'pending-guard', 'message': '로그인 장애를 진단해주세요'}
    first = client.post('/chat', json=body).json()
    assert first['metadata']['status'] == 'needs_clarification'
    before = client.get('/sessions/pending-guard').json()
    rejected = client.post('/chat', json={**body, 'message': '오늘 날씨 알려줘'}).json()
    assert rejected['metadata']['status'] == 'rejected'
    assert client.get('/sessions/pending-guard').json() == before
    resumed = client.post('/chat', json={**body, 'message': 'auth-service'}).json()
    assert resumed['report']['targets'] == ['auth-service']
    assert '로그인 장애' in resumed['report']['question']


def test_short_followup_uses_existing_target_instead_of_general_chat(client):
    client.post('/chat', json={'thread_id': 'short-followup', 'message': 'auth-service 로그인 장애 진단'})
    result = client.post('/chat', json={'thread_id': 'short-followup', 'message': '왜?'}).json()
    assert result['metadata']['route'] == 'incident'
    assert result['report']['targets'] == ['auth-service'] and '로그인 장애' in result['report']['question']
