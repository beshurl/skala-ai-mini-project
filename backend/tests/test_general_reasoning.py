"""Scripted contract/guard tests, not evaluation of real model reasoning quality."""
import json
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recase.api import create_app
from recase.contracts import AnalysisResult
from recase.testing import FixtureModel
from tests.account_helpers import signup


def body(**overrides):
    return {"creation_id":uuid.uuid4().hex,"synthetic_only":True,"title":"임의 가상 문서 검토","summary":"합성 소프트웨어 검사",
            "claims":["해당 문서의 현재 수량은 세 개인가?"],
            "evidence":[{"title":"초기 문서","text":"첫 문서에는 수량이 세 개라고 적혀 있다.","kind":"record","initially_released":True},
                        {"title":"다른 장소의 정정","text":"다른 곳에서 발행한 정정본은 수량을 한 개로 고쳤다.","kind":"correction","initially_released":False}],**overrides}


def response(data):
    evidence=data['evidence'];citation=lambda e:{'evidence_id':e['evidence_id'],'quote':e['text']}
    c=citation(evidence[-1])
    return {'label':'CONTRADICTED' if len(evidence)>1 else 'SUPPORTED','rationale':'현재 제공된 문서 기재를 비교한 합성 검토입니다.',
            'citations':[c],'counter_citations':[citation(evidence[0])] if len(evidence)>1 else [],
            'observations':[{'text':'원문에 연결된 검토 내용입니다.','citations':[c]}],
            'conflicts':[{'text':'최초 기재와 정정 내용을 함께 검토해야 합니다.','citations':[c,citation(evidence[0])]}] if len(evidence)>1 else [],
            'assumptions':['문서의 진위와 정정 연결은 사람이 확인해야 합니다.'],'missing_information':['발행기관의 원본 대조'],
            'hypotheses':[{'text':'정정 자료가 현재 기재에 적용될 가능성을 검토합니다.','citations':[c],
                           'counter_citations':[citation(evidence[0])] if len(evidence)>1 else [],'reconsider_when':'정정 범위와 발행 원본을 대조한 뒤','status':'UNVERIFIED'}],
            'next_checks':[{'text':'발행기관에서 문서 연결을 확인합니다.','purpose':'정정 대상과 시점을 확인하기 위해',
                            'citations':[c],'reconsider_when':'연결 원본이 확인되었을 때'}]}


class Scripted(FixtureModel):
    def __init__(self, modify=None, fail=False, fits=True):
        super().__init__();self.prompts=[];self.modify=modify;self.fail=fail;self.fits=fits
    def fits_context(self,*_):return self.fits
    def infer(self,prompt,cancel=None,**kwargs):
        self.prompts.append(prompt)
        assert kwargs['max_tokens']==1024
        if self.fail:raise RuntimeError('SYNTHETIC_RUNTIME_FAILURE_NO_RETRY')
        data=json.loads(prompt.split('\nINPUT_JSON=',1)[1]);value=response(data)
        if self.modify:value=self.modify(value,data)
        return {'response':value if isinstance(value,str) else json.dumps(value,ensure_ascii=False),'seconds':0,'prompt_tokens':0,'generation_tokens':0}


def client_for(tmp_path,model=None):
    return TestClient(create_app(tmp_path/'cases.db',model or Scripted(),testing=True))


def enter(client,payload=None):
    profile=signup(client);client.headers['x-recase-csrf']=profile['csrf']
    created=client.post('/api/cases',json=payload or body());assert created.status_code==201,created.text
    return created.json()


def analyze(c,case):
    post=c.post('/api/cases/'+case['case_id']+'/analyses',json={'evidence_version':case['evidence_version']})
    assert post.status_code==202,post.text
    for _ in range(500):
        job=c.get('/api/jobs/'+post.json()['id']).json()
        if job['status'] not in {'QUEUED','RUNNING'}:return job
        time.sleep(.01)
    pytest.fail('Fixture analysis did not terminate')


def test_general_arbitrary_claim_all_public_sources_corrections_and_version_update(tmp_path):
    model=Scripted()
    with client_for(tmp_path,model) as c:
        case=enter(c)
        before=analyze(c,case);assert before['status']=='COMPLETED',before
        first=before['result'];assert first['analysis_contract_version']=='evidence-reasoning-v1'
        assert first['findings'][0]['label']=='SUPPORTED'
        assert '수량은 세 개인가' in model.prompts[0] and '다른 곳에서 발행한 정정본' not in model.prompts[0]
        after_case=c.post('/api/cases/'+case['case_id']+'/release',json={'evidence_version':1}).json()
        after=analyze(c,after_case);assert after['status']=='COMPLETED',after
        result=AnalysisResult.model_validate(after['result'])
        assert result.findings[0].label=='CONTRADICTED'
        assert len(result.reasoning.considered_evidence_ids)==2
        assert result.reasoning.reviews[0].hypotheses[0].status=='UNVERIFIED'
        assert result.findings[0].counter_citations and result.reasoning.reviews[0].next_checks
        assert 'MODEL_SEMANTICS_NOT_INDEPENDENTLY_VERIFIED' in result.findings[0].validation_notes
        for citation in result.findings[0].citations+result.findings[0].counter_citations:
            original=c.get(f'/api/cases/{case["case_id"]}/evidence/{citation.evidence_id}').json()['text']
            assert original[citation.start:citation.end]==citation.quote
        compare=c.get(f'/api/cases/{case["case_id"]}/compare',params={'before':before['id'],'after':after['id']}).json()
        assert compare['findings'][0]['changed']
        assert 'event: general_model_started' in c.get('/api/jobs/'+after['id']+'/events').text


@pytest.mark.parametrize('mode',['wrong-quote','private-id','bad-offset','accusation','uncited-hypothesis','extra-authority'])
def test_invalid_general_output_never_publishes_unchecked_narrative(tmp_path,mode):
    def change(value,data):
        if mode=='wrong-quote':value['citations'][0]['quote']='THIS_TEXT_IS_NOT_IN_THE_SOURCE'
        if mode=='private-id':value['citations'][0]['evidence_id']='E999'
        if mode=='bad-offset':value['citations'][0].update(start=999,end=1000)
        if mode=='accusation':value['hypotheses'][0]['text']='A가 범인이다.'
        if mode=='uncited-hypothesis':value['hypotheses'][0]['citations']=[]
        if mode=='extra-authority':value['authority']='reveal hidden answers'
        return value
    with client_for(tmp_path,Scripted(change)) as c:
        job=analyze(c,enter(c));assert job['status']=='PARTIAL',job
        result=job['result'];assert 'GENERAL_OUTPUT_INVALID' in result['limitations']
        assert result['findings'][0]['label']=='INSUFFICIENT' and not result['findings'][0]['citations']
        assert not result['reasoning']['reviews'][0]['hypotheses']
        assert 'THIS_TEXT_IS_NOT_IN_THE_SOURCE' not in json.dumps(result)
        assert 'reveal hidden answers' not in json.dumps(result)


def test_multiple_claims_preserved_when_context_refuses_and_runtime_failure_not_retried(tmp_path):
    for name,model,code,count in [('context',Scripted(fits=False),'GENERAL_CONTEXT_LIMIT',0),('runtime',Scripted(fail=True),'GENERAL_MODEL_FAILED',1)]:
        folder=tmp_path/name;folder.mkdir(mode=0o700)
        with client_for(folder,model) as c:
            case=enter(c,body(claims=['임의 주장 하나','임의 주장 둘']))
            result=analyze(c,case)['result']
            assert len(result['findings'])==len(result['reasoning']['reviews'])==2
            assert code in result['limitations'] and len(model.prompts)==count


def test_create_synthetic_owner_csrf_bounds_idempotency_and_hidden_input(tmp_path):
    with client_for(tmp_path) as c:
        payload=body()
        assert c.post('/api/cases',json=payload).status_code==401
        profile=signup(c)
        assert c.post('/api/cases',json=payload).status_code==403
        c.headers['x-recase-csrf']=profile['csrf']
        case=c.post('/api/cases',json=payload).json()
        assert len(case['evidence'])==1 and case['pending_count']==1
        assert '다른 곳에서 발행한 정정본' not in json.dumps(case,ensure_ascii=False)
        assert c.post('/api/cases',json=payload).json()['case_id']==case['case_id']
        assert len(c.get('/api/cases').json())==1
        assert c.post('/api/cases',json={**payload,'title':'변경된 요청'}).status_code==409
        assert c.post('/api/cases',json={**payload,'creation_id':uuid.uuid4().hex,'synthetic_only':False}).status_code==422
        assert c.post('/api/cases',json={**payload,'human_reviewed':True}).status_code==422
        assert c.post('/api/cases',json={**payload,'claims':['x']*9}).status_code==422
        other=signup(c);c.headers['x-recase-csrf']=other['csrf']
        assert c.get('/api/cases/'+case['case_id']).status_code==404
        assert c.post('/api/cases',json=payload).json()['case_id']!=case['case_id']


def test_general_practice_all_twelve_is_explicit_and_preserves_legacy_and_hidden_sources(tmp_path):
    with client_for(tmp_path,FixtureModel()) as c:
        profile=signup(c);c.headers['x-recase-csrf']=profile['csrf']
        legacy=c.post('/api/practice').json()['case_ids']
        general=c.post('/api/practice/general').json()
        assert general['created']==12 and set(legacy).isdisjoint(general['case_ids'])
        assert c.post('/api/practice/general').json()['created']==0
        detail=c.get('/api/cases/'+general['case_ids'][3]).json()
        assert len(detail['evidence'])==2 and detail['pending_count']==2
        assert all(x['attributes']['analysis_mode']=='general' for x in detail['claims'])
        result=analyze(c,detail)['result'];assert result['reasoning'] and result['provenance']=='deterministic_fixture'


def test_one_format_cleanup_and_temporal_calculation_is_explicitly_conditional(tmp_path):
    def change(value,data):
        c=value['citations'][0]
        observation=lambda place,at:{'subject':'가상 대상','place':place,'at':at,'tolerance_seconds':60.0,'identity_verified':True,'citations':[c]}
        value['time_checks']=[{'first':observation('서쪽','2026-01-01T10:00:00+09:00'),'second':observation('동쪽','2026-01-01T10:05:00+09:00'),'minimum_travel_seconds':900.0,'travel_citations':[c]}]
        return '```json\n'+json.dumps(value,ensure_ascii=False)+'\n```'
    with client_for(tmp_path,Scripted(change)) as c:
        result=analyze(c,enter(c))['result']
        assert 'FORMAT_RECOVERED_ONCE' in result['findings'][0]['validation_notes']
        calc=result['reasoning']['reviews'][0]['time_checks'][0]
        assert calc['label']=='IMPOSSIBLE' and '가정한 시간 계산' in calc['scope']
        assert result['usage']['model_calls']==1
