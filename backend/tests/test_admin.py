import json
import time
import pytest
from fastapi.testclient import TestClient
from recase.api import create_app
from tests.account_helpers import PASSWORD, signup, enter_demo
from recase.observability import Observations
from recase.testing import FixtureModel


@pytest.fixture
def operator(tmp_path):
    app = create_app(tmp_path / 'demo.db', FixtureModel(), testing=True)
    with TestClient(app) as client:
        app.state.accounts.create('operator@example.test', PASSWORD, 'UNIT_TEST_OPERATOR', role='admin')
        signup(client, 'user@example.test')
        yield client, tmp_path


def login(client, path):
    response = client.post('/api/auth/login', json={'email':'operator@example.test','password':PASSWORD})
    assert response.status_code == 200
    return response


def analyze(client):
    session = enter_demo(client).json()
    case = client.get('/api/cases').json()[0]
    response = client.post(f'/api/cases/{case["id"]}/analyses', json={'evidence_version':1}, headers={'x-recase-csrf':session['csrf']})
    assert response.status_code == 202
    job = response.json()
    for _ in range(100):
        job = client.get('/api/jobs/' + job['id']).json()
        if job['status'] not in {'QUEUED','RUNNING'}:
            return response, job
        time.sleep(.01)
    pytest.fail('analysis did not finish')


def test_admin_role_separate_from_user_and_csrf_logout(operator):
    c, path = operator
    assert c.get('/api/admin/summary').status_code == 403
    assert c.get('/api/admin/logs').status_code == 403
    user = c.post('/api/auth/login', json={'email':'user@example.test','password':PASSWORD})
    assert user.status_code == 200 and user.json()['role'] == 'user'
    assert c.get('/api/admin/summary').status_code == 403
    response = login(c,path)
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=strict' in response.headers['set-cookie']
    assert 'Path=/' in response.headers['set-cookie']
    assert c.get('/api/admin/session').json()['role'] == 'admin'
    assert c.get('/api/admin/summary').status_code == 200
    c.app.state.ready=False
    snapshot=c.get('/api/admin/summary').json()
    assert snapshot['ready'] is False and snapshot['mcp_connected'] is True
    c.app.state.ready=True
    assert c.post('/api/auth/logout').status_code == 403
    assert c.post('/api/auth/logout', headers={'x-recase-csrf':response.json()['csrf']}).status_code == 200
    assert c.get('/api/admin/summary').status_code == 401
    login(c,path)
    c.cookies.clear()
    assert c.get('/api/admin/summary').status_code == 401


def test_real_metadata_correlates_and_redacts_content(operator):
    c,path = operator
    login(c,path)
    canary = 'PRIVATE-secret-prompt-DO-NOT-LOG'
    response, job = analyze(c)
    assert job['status'] == 'COMPLETED'
    c.get('/api/cases?query='+canary, headers={'x-trace-id':canary})
    c.post('/api/auth/login',json={'email':'unknown@example.test','password':canary})
    rows = c.get('/api/admin/logs',params={'trace_id':job['id']}).json()['items']
    assert {r['component'] for r in rows} >= {'http','llm','rag','mcp','system'}
    assert {r['request_id'] for r in rows} == {response.headers['x-request-id']}
    rag = next(r for r in rows if r['component']=='rag')
    assert rag['hit_count'] > 0 and all(set(d)=={'id','score'} for d in rag['documents'])
    llm = next(r for r in rows if r['component']=='llm')
    assert llm['duration_ms'] >= 0 and llm['input_tokens'] == 0
    output = c.get('/api/admin/logs').text
    assert canary not in output and '보관실에' not in output and 'access_key' not in output
    assert str(path) not in output
    summary = c.get('/api/admin/summary').json()
    assert summary['metrics']['llm']['count'] == 1
    assert summary['tool_metrics']['get_public_case']['count']==1
    assert summary['tool_metrics']['search_case_evidence']['success_rate']==1
    assert summary['tool_metrics']['read_evidence']['count']==0
    assert summary['tool_metrics']['read_evidence']['success_rate'] is None
    assert summary['search'] == {'method':'keyword-bigram-v1','reference_corpus':'BLOCKED','vector':False,'hybrid':False,'rerank':False}
    assert summary['memory'] is None and summary['cpu'] is None
    assert c.get('/api/admin/logs', params={'limit':1,'offset':0}).json()['items'][0]['id'] > c.get('/api/admin/logs',params={'limit':1,'offset':2}).json()['items'][0]['id']
    assert c.get('/api/admin/logs',params={'q':"' OR 1=1--"}).json()['total'] == 0
    assert c.get('/api/admin/logs',params={'level':'debug'}).status_code == 422
    assert c.get('/api/admin/logs',params={'limit':101}).status_code == 422
    assert c.get('/api/admin/summary',params={'seconds':9999999}).status_code == 422


def test_failed_model_records_attempt_not_secret_exception(operator):
    c,path = operator
    login(c,path)
    def failed(*args):
        raise RuntimeError('DO-NOT-LOG /private/gold SECRET')
    c.app.state.model.infer = failed
    _, job = analyze(c)
    assert job['status']=='FAILED'
    rows = c.get('/api/admin/logs',params={'component':'llm','errors_only':True}).json()['items']
    assert len(rows)==1 and rows[0]['error']=='MODEL_INFERENCE_FAILED'
    assert rows[0]['input_tokens'] is None
    assert 'DO-NOT-LOG' not in json.dumps(rows)


def test_account_reset_origin_rate_and_body_limit(operator, tmp_path):
    c,path = operator
    body={'email':'operator@example.test','password':'incorrect'}
    assert c.post('/api/auth/login',json=body,headers={'origin':'https://evil.example'}).status_code==403
    for _ in range(8):
        assert c.post('/api/auth/login',json=body).status_code==401
    assert c.post('/api/auth/login',json=body).status_code==429
    assert c.post('/api/demo',content=b'x'*65537).status_code==413
    def chunks():
        yield b'x'*32000
        yield b'x'*34000
    assert c.post('/api/demo',content=chunks()).status_code==413
    with TestClient(create_app(path/'second.db',FixtureModel(),testing=True,accounts_path=c.app.state.accounts.path)) as other:
        login(other,path)
        other.app.state.accounts.reset_password('operator@example.test',PASSWORD+'-rotated')
        assert other.get('/api/admin/summary').status_code==401


def test_observation_allowlist_retention_and_exact_percentiles(tmp_path):
    obs = Observations(tmp_path/'safe.db',capacity=3)
    for i in range(1,6):
        obs.record(component='http',event='request_finished',duration_ms=i,route='/private/gold',request_id='SECRET',trace_id='SECRET',error='secret exception')
    rows = obs.logs(since=0)['items']
    assert len(rows)==3 and all(r['route'] is None and r['request_id'] is None and r['trace_id'] is None and r['error'] is None for r in rows)
    metric=obs.summary(60)['metrics']['http']
    assert metric['average_ms']==4 and metric['p50_ms']==4 and metric['p95_ms']==5
    obs.record(component='secret',event='anything')
    assert obs.summary(60)['dropped']==1
    assert obs.path.stat().st_mode & 0o777==0o600
    obs.record(component='system',event='analysis_finished',outcome='CANCELLED',error='CANCELLED')
    assert obs.summary(60)['error_groups']==[]


def test_same_password_does_not_grant_another_accounts_admin_role(operator):
    c,path=operator
    assert c.post('/api/auth/login',json={'email':'user@example.test','password':PASSWORD}).json()['role']=='user'
    assert c.get('/api/admin/summary').status_code==403
    assert login(c,path).json()['role']=='admin'


def test_mcp_failure_and_empty_search_observations(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from recase.mcp_client import EvidenceClient
    obs=Observations(tmp_path/'observations.db')
    class Session:
        fail=False
        async def call_tool(self,*args,**kwargs):
            if self.fail:raise TimeoutError('secret /private/gold prompt')
            return SimpleNamespace(isError=False,structuredContent={'hits':[]})
    async def check():
        session=Session();mcp=EvidenceClient(session,'secret',obs)
        assert await mcp.call('search_case_evidence','owner','case',1,query='PRIVATE_QUERY')=={'hits':[]}
        session.fail=True
        with pytest.raises(RuntimeError,match='^MCP_TOOL_FAILED$'):
            await mcp.call('search_case_evidence','owner','case',1,query='PRIVATE_QUERY')
    asyncio.run(check())
    rows=obs.logs(since=0)['items']
    assert len(rows)==4 and sum(r['outcome']=='ERROR' for r in rows)==2
    assert next(r for r in rows if r['component']=='rag' and r['outcome']=='SUCCESS')['hit_count']==0
    assert 'PRIVATE_QUERY' not in json.dumps(rows) and '/private/gold' not in json.dumps(rows)
