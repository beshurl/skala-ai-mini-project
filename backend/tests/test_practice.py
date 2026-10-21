"""Practice content/ownership/release checks, not real-model accuracy claims."""
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from recase.api import create_app
from recase.practice import bundle
from recase.testing import FixtureModel
from tests.account_helpers import signup


def test_release_allows_only_practice_input_not_review_reference():
    from recase.release_validation import allowed_release_path
    assert allowed_release_path('data/practice/v1/cases.json')
    assert not allowed_release_path('docs/practice/v1/review_reference.json')
    assert not allowed_release_path('data/practice/v1/review_reference.json')
    assert not allowed_release_path('runtime/recase.accounts.sqlite3')


def test_practice_bundle_is_exposed_synthetic_and_reference_stays_outside_service():
    data, revision = bundle()
    assert len(revision) == 64 and len(data["cases"]) == 12
    assert data["human_reviewed"] is False and data["independent_final_set"] is False
    assert len([c for c in data["cases"] if c["automatic_demo"]]) == 3
    assert sum(len(c["evidence"]) for c in data["cases"]) == 48
    assert sum(len(c["stages"]) for c in data["cases"]) == 36
    assert "proposed_relation" not in json.dumps(data)


def test_practice_requires_account_csrf_and_preserves_existing_versions(tmp_path):
    with TestClient(create_app(tmp_path/'cases.db', model=FixtureModel(), testing=True)) as client:
        assert client.post('/api/practice').status_code == 401
        user = signup(client)
        assert client.post('/api/practice').status_code == 403
        client.headers['x-recase-csrf'] = user['csrf']
        seeded = client.post('/api/practice')
        assert seeded.status_code == 201 and seeded.json()['created'] == 3
        ids = seeded.json()['case_ids']
        detail = client.get('/api/cases/'+ids[0]).json()
        assert len(detail['evidence']) == 2 and detail['pending_count'] == 2
        hidden_text = bundle()[0]['cases'][0]['evidence'][2]['text']
        assert hidden_text not in json.dumps(detail, ensure_ascii=False)
        assert 'proposed_relation' not in seeded.text
        assert client.post('/api/cases/'+ids[0]+'/release',json={'evidence_version':1}).status_code == 200
        again = client.post('/api/practice').json()
        assert again['created'] == 0 and again['case_ids'] == ids
        assert client.get('/api/cases/'+ids[0]).json()['evidence_version'] == 2
        assert len(client.get('/api/cases').json()) == 3
        other = signup(client)
        client.headers['x-recase-csrf'] = other['csrf']
        assert client.get('/api/cases/'+ids[0]).status_code == 404
        assert client.post('/api/practice').json()['created'] == 3
        assert set(ids).isdisjoint(c['id'] for c in client.get('/api/cases').json())
        assert client.get('/docs/practice/v1/review_reference.json').status_code == 404


def test_nine_supported_fixture_stages_run_without_using_review_reference(tmp_path):
    reference = json.loads((Path(__file__).resolve().parents[2]/'docs/practice/v1/review_reference.json').read_text())
    expected = {(r['case_id'],r['version']):r['proposed_relation'] for r in reference['checks']}
    with TestClient(create_app(tmp_path/'cases.db', model=FixtureModel(), testing=True)) as client:
        user = signup(client);client.headers['x-recase-csrf'] = user['csrf']
        ids = client.post('/api/practice').json()['case_ids']
        for key, case_id in zip(('P01','P02','P03'),ids,strict=True):
            for version in (1,2,3):
                if version>1:
                    assert client.post(f'/api/cases/{case_id}/release',json={'evidence_version':version-1}).status_code == 200
                created=client.post(f'/api/cases/{case_id}/analyses',json={'evidence_version':version})
                assert created.status_code == 202
                job_id=created.json()['id']
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    job=client.get('/api/jobs/'+job_id).json()
                    if job['status'] not in ('QUEUED','RUNNING'):break
                    time.sleep(.02)
                if key == 'P03' and version < 3:
                    assert job['status']=='PARTIAL',job
                    assert 'RETRIEVAL_INSUFFICIENT' in job['result']['limitations']
                else:
                    assert job['status']=='COMPLETED',job
                result=job['result']
                assert result['provenance']=='deterministic_fixture'
                assert result['findings'][0]['label']==expected[(key,version)]
                visible={e['id'] for e in client.get('/api/cases/'+case_id).json()['evidence']}
                assert set(result['findings'][0]['evidence_ids']).issubset(visible)
