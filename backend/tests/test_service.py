from tests.account_helpers import enter_demo
import asyncio
import json
import time
import pytest
from fastapi.testclient import TestClient
from recase.api import create_app
from recase.capability import mint
from recase.mcp_client import connect
from recase.store import Store, Conflict, NotFound
from recase.testing import FixtureModel


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "service.sqlite3", FixtureModel(), testing=True)
    with TestClient(app) as c:
        yield c


def enter(client):
    session = enter_demo(client).json()
    client.headers["x-recase-csrf"] = session["csrf"]
    case = client.get("/api/cases").json()[0]
    return case, session


def wait_job(client, job):
    for _ in range(300):
        data = client.get("/api/jobs/" + job["id"]).json()
        if data["status"] not in ("QUEUED", "RUNNING"):
            return data
        time.sleep(.01)
    pytest.fail("Job did not terminate")


def run_job(client, case):
    response = client.post(f'/api/cases/{case["id"]}/analyses', json={"evidence_version": case.get("version", case.get("evidence_version"))})
    assert response.status_code == 202, response.text
    return wait_job(client, response.json())


def test_complete_update_irrelevant_update_compare_and_sse(client):
    case, _ = enter(client)
    before = run_job(client, case)
    assert before["status"] == "COMPLETED"
    assert before["result"]["provenance"] == "deterministic_fixture"
    assert before["result"]["findings"][0]["label"] == "INSUFFICIENT"
    released = client.post(f'/api/cases/{case["id"]}/release', json={"evidence_version": 1}).json()
    after = run_job(client, {**released, "id": case["id"]})
    assert after["result"]["findings"][0]["label"] == "CONTRADICTED"
    comparison = client.get(f'/api/cases/{case["id"]}/compare', params={"before": before["id"], "after": after["id"]}).json()
    assert comparison["findings"][0]["changed"] is True
    released = client.post(f'/api/cases/{case["id"]}/release', json={"evidence_version": 2}).json()
    unchanged = run_job(client, {**released, "id": case["id"]})
    assert unchanged["result"]["findings"] == after["result"]["findings"]
    stream = client.get(f'/api/jobs/{after["id"]}/events')
    assert 'event: completed' in stream.text and 'event: retrieval_complete' in stream.text
    event_id = client.app.state.store.events(client.get('/api/session').json()['user_id'], after['id'])[-1]['id']
    assert client.get(f'/api/jobs/{after["id"]}/events', headers={"last-event-id": str(event_id)}).text == ""
    finding = after["result"]["findings"][0]
    for evidence_id in finding["evidence_ids"]:
        assert client.get(f'/api/cases/{case["id"]}/evidence/{evidence_id}').status_code == 200


def test_auth_csrf_origin_and_private_data(client):
    assert client.get('/api/cases').status_code == 401
    case, s = enter(client)
    detail = client.get(f'/api/cases/{case["id"]}').json()
    assert len(detail['evidence']) == 2 and detail['pending_count'] == 2
    with client.app.state.store.db() as db:
        private_id = db.execute('SELECT id FROM evidence WHERE case_id=? AND released_version IS NULL', (case['id'],)).fetchone()[0]
    assert private_id not in json.dumps(detail)
    assert client.get(f'/api/cases/{case["id"]}/evidence/{private_id}').status_code == 404
    assert client.post(f'/api/cases/{case["id"]}/release', json={'evidence_version':1}, headers={'x-recase-csrf':'forged'}).status_code == 403
    assert client.get('/api/cases', headers={'origin':'https://evil.example'}).status_code == 403
    assert client.get('/api/cases', headers={'host':'evil.example'}).status_code == 400
    assert client.post(f'/api/cases/{case["id"]}/release', json={'evidence_version':99}).status_code == 409
    assert client.post(f'/api/cases/{case["id"]}/release', json={'evidence_version':1,'evidence_id':private_id}).status_code == 422


def test_user_isolation_in_case_result_stream_and_compare(client):
    case, _ = enter(client)
    job = run_job(client, case)
    client.cookies.clear()
    other, _ = enter(client)
    assert case['id'] not in json.dumps(client.get('/api/cases').json())
    for url in [f'/api/cases/{case["id"]}', f'/api/jobs/{job["id"]}', f'/api/jobs/{job["id"]}/events', f'/api/cases/{case["id"]}/analyses']:
        assert client.get(url).status_code == 404
    assert client.post(f'/api/jobs/{job["id"]}/cancel').status_code == 404
    assert client.get(f'/api/cases/{other["id"]}/compare', params={'before':job['id'],'after':job['id']}).status_code == 404


def test_stale_cancel_timeout_and_invalid_output(client):
    case, _ = enter(client)
    client.app.state.model.delay = .3
    job = client.post(f'/api/cases/{case["id"]}/analyses', json={'evidence_version':1}).json()
    assert client.post(f'/api/cases/{case["id"]}/analyses', json={'evidence_version':1}).status_code == 409
    assert client.post(f'/api/cases/{case["id"]}/release', json={'evidence_version':1}).status_code == 200
    stale = wait_job(client, job)
    assert stale['status'] == 'STALE' and stale['result'] is None
    job = client.post(f'/api/cases/{case["id"]}/analyses', json={'evidence_version':2}).json()
    client.post(f'/api/jobs/{job["id"]}/cancel')
    assert wait_job(client, job)['status'] == 'CANCELLED'
    client.app.state.worker.timeout = .02
    failed = run_job(client, {**case,'version':2})
    assert failed['status'] == 'FAILED' and failed['error'] == 'ANALYSIS_TIMEOUT'
    client.app.state.worker.timeout = 180
    client.app.state.model.delay, client.app.state.model.invalid = 0, True
    partial = run_job(client, {**case,'version':2})
    assert partial['status'] == 'PARTIAL'
    assert 'MODEL_OUTPUT_INVALID' in partial['result']['limitations']


def test_restart_and_actual_backup_restore(tmp_path):
    store = Store(tmp_path/'source.db')
    s = store.new_demo(); case = store.cases(s['user_id'])[0]
    job = store.create_job(s['user_id'], case['id'], 1, {'backend':'fixture'})
    backup = store.backup(tmp_path/'backup.db')
    restored = Store(backup)
    assert restored.snapshot(s['user_id'], case['id']) == store.snapshot(s['user_id'], case['id'])
    assert restored.recover() == 1
    assert restored.job(s['user_id'],job['id'])['error'] == 'SERVER_RESTARTED'
    assert store.job(s['user_id'],job['id'])['status'] == 'QUEUED'
    assert restored.events(s['user_id'], job['id'])[-1]['type'] == 'failed'


def test_mcp_real_stdio_scopes_hidden_evidence_and_no_reference_fallback(tmp_path):
    store = Store(tmp_path/'mcp.db'); s=store.new_demo(); case=store.cases(s['user_id'])[0]
    with store.db() as db:
        hidden=db.execute('SELECT id FROM evidence WHERE case_id=? AND released_version IS NULL',(case['id'],)).fetchone()[0]
    async def scenario():
        async with connect(store.path, 'test-secret') as mcp:
            public=await mcp.call('get_public_case',s['user_id'],case['id'],1)
            assert hidden not in json.dumps(public)
            with pytest.raises(RuntimeError):
                await mcp.call('read_evidence',s['user_id'],case['id'],1,evidence_id=hidden)
            with pytest.raises(RuntimeError):
                await mcp.call('get_public_case','attacker',case['id'],1)
            with pytest.raises(RuntimeError):
                await mcp.call('get_public_case',s['user_id'],'foreign',1)
            forged = await mcp.session.call_tool('get_public_case', {'case_id':case['id'],'evidence_version':1,'access_token':'forged'})
            assert forged.isError is True
            refs=await mcp.call('search_reference_judgments',s['user_id'],case['id'],1,query='판례')
            assert refs['status']=='BLOCKED' and refs['hits']==[]
    asyncio.run(scenario())
