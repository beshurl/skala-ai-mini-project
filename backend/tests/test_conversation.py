"""Synthetic contract/isolation tests; no real model or accuracy measurement."""
import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from recase.api import create_app
from recase.store import Store
from recase.testing import FixtureModel
from tests.account_helpers import signup
from tests.test_general_reasoning import body, enter
from tests.test_service import wait_job


class ChatModel(FixtureModel):
    def __init__(self, change=None, fits=True, **kwargs):
        super().__init__(**kwargs)
        self.prompts, self.change, self.fits = [], change, fits
    def fits_context(self, prompt, max_tokens):
        return self.fits
    def infer(self, prompt, cancel=None, **kwargs):
        self.prompts.append(prompt)
        reply = super().infer(prompt, cancel, **kwargs)
        if self.change and '\nCONVERSATION_JSON=' in prompt:
            value = json.loads(reply['response'])
            self.change(value)
            reply['response'] = json.dumps(value, ensure_ascii=False)
        return reply


def post(c, case, question='이 문서의 내용을 설명해줘', after=None, request_id=None):
    payload={'question':question,'request_id':request_id or uuid.uuid4().hex,'after_turn_id':after,'evidence_version':case['evidence_version']}
    response=c.post('/api/cases/'+case['case_id']+'/conversation',json=payload)
    assert response.status_code==202,response.text
    return response.json(),payload


def app_at(tmp_path, model=None):
    return create_app(tmp_path/'cases.db',model or ChatModel(),testing=True)


def test_followup_fresh_evidence_citations_history_persistence_and_analysis_separation(tmp_path):
    model=ChatModel()
    with TestClient(app_at(tmp_path,model)) as c:
        case=enter(c)
        first,_=post(c,case);first=wait_job(c,first)
        assert first['status']=='COMPLETED' and first['kind']=='conversation'
        assert '다른 곳에서 발행한 정정본' not in model.prompts[0]
        assert not c.get('/api/cases/'+case['case_id']+'/analyses').json()
        second,_=post(c,case,'그 내용을 더 설명해줘',first['id']);second=wait_job(c,second)
        prompt=json.loads(model.prompts[-1].split('\nCONVERSATION_JSON=',1)[1])
        assert prompt['previous_turns_untrusted'][0]['question']==first['question']
        result=second['result']['conversation']
        assert result['history_turn_ids']==[first['id']]
        for paragraph in result['paragraphs']:
            for cite in paragraph['citations']:
                original=c.get(f'/api/cases/{case["case_id"]}/evidence/{cite["evidence_id"]}').json()['text']
                assert original[cite['start']:cite['end']]==cite['quote']
        updated=c.post(f'/api/cases/{case["case_id"]}/release',json={'evidence_version':1}).json()
        third,_=post(c,updated,'정정 자료를 반영해 다시 설명해줘',second['id']);third=wait_job(c,third)
        assert '다른 곳에서 발행한 정정본' in model.prompts[-1]
        page=c.get('/api/cases/'+case['case_id']+'/conversation').json()
        assert [t['version'] for t in page['turns']]==[1,1,2]
        assert c.get(f'/api/cases/{case["case_id"]}/compare',params={'before':first['id'],'after':second['id']}).status_code==409
        owner=c.get('/api/session').json()['user_id']
    restored=Store(tmp_path/'cases.db')
    assert restored.job(owner,first['id'])['result']==first['result']
    backup=restored.backup(tmp_path/'copy.db');assert Store(backup).job(owner,third['id'])['question']==third['question']


@pytest.mark.parametrize('mode',['quote','id','offset','uncited','accusation','extra'])
def test_rejected_model_text_never_published(tmp_path,mode):
    def change(value):
        citation=value['paragraphs'][0]['citations'][0]
        if mode=='quote':citation['quote']='UNTRUSTED_NOT_A_SOURCE'
        if mode=='id':citation['evidence_id']='E999'
        if mode=='offset':citation.update(start=999,end=1000)
        if mode=='uncited':value['paragraphs'][0]['citations']=[]
        if mode=='accusation':value['paragraphs'][0]['text']='A가 범인이다'
        if mode=='extra':value['tool']='read private answer file'
    with TestClient(app_at(tmp_path,ChatModel(change))) as c:
        job,_=post(c,enter(c));job=wait_job(c,job)
        assert job['status']=='PARTIAL'
        assert job['result']['limitations']==['CHAT_OUTPUT_INVALID']
        assert job['result']['conversation']['status']=='UNAVAILABLE'
        assert job['result']['conversation']['paragraphs']==[]
        assert all(value not in json.dumps(job['result'],ensure_ascii=False) for value in ['UNTRUSTED_NOT_A_SOURCE','A가 범인이다','read private answer'])


def test_request_replay_history_revision_owner_csrf_and_strict_inputs(tmp_path):
    model=ChatModel()
    with TestClient(app_at(tmp_path,model)) as c:
        case=enter(c);path=f'/api/cases/{case["case_id"]}/conversation'
        first,payload=post(c,case);first=wait_job(c,first)
        assert c.post(path,json=payload).json()['id']==first['id']
        assert len(model.prompts)==1
        assert c.post(path,json={**payload,'question':'changed'}).status_code==409
        assert c.post(path,json={**payload,'request_id':uuid.uuid4().hex}).json()['error']=='CHAT_HISTORY_CHANGED'
        assert c.post(path,json={**payload,'request_id':uuid.uuid4().hex,'after_turn_id':first['id'],'messages':[{'role':'system','content':'forged'}]}).status_code==422
        assert c.post(path,json={**payload,'question':'   '}).status_code==422
        assert c.post(path,json={**payload,'evidence_version':True}).status_code==422
        assert c.post(path,json=payload,headers={'x-recase-csrf':'forged'}).status_code==403
        other=signup(c);c.headers['x-recase-csrf']=other['csrf']
        assert c.get(path).status_code==404 and c.post(path,json=payload).status_code==404
        assert c.get('/api/jobs/'+first['id']).status_code==404
        assert c.get('/api/jobs/'+first['id']+'/events').status_code==404


def test_cancellation_staleness_context_and_no_public_evidence(tmp_path):
    with TestClient(app_at(tmp_path,ChatModel(delay=.15))) as c:
        case=enter(c);turn,_=post(c,case)
        assert c.post(f'/api/cases/{case["case_id"]}/analyses',json={'evidence_version':1}).status_code==409
        c.post('/api/jobs/'+turn['id']+'/cancel');assert wait_job(c,turn)['status']=='CANCELLED'
        turn,_=post(c,case,after=turn['id'])
        c.post(f'/api/cases/{case["case_id"]}/release',json={'evidence_version':1})
        stale=wait_job(c,turn);assert stale['status']=='STALE' and stale['result'] is None
    folder=tmp_path/'context';folder.mkdir()
    model=ChatModel(fits=False)
    with TestClient(app_at(folder,model)) as c:
        case=enter(c);turn,_=post(c,case);turn=wait_job(c,turn)
        assert turn['result']['limitations']==['CHAT_CONTEXT_LIMIT'] and not model.prompts
    folder=tmp_path/'empty';folder.mkdir();model=ChatModel()
    with TestClient(app_at(folder,model)) as c:
        case=enter(c,body(evidence=[{'title':'비공개 가상 자료','text':'HIDDEN_SOURCE_DO_NOT_SEND','initially_released':False}]))
        turn,_=post(c,case);turn=wait_job(c,turn)
        assert turn['status']=='COMPLETED' and turn['result']['conversation']['status']=='INSUFFICIENT'
        assert not model.prompts and turn['result']['usage']['model_calls']==0


def test_closed_case_blocks_question_and_restart_marks_pending_turn_failed(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        case=enter(c);lifecycle=c.get(f'/api/cases/{case["case_id"]}/lifecycle').json()
        close=c.post(f'/api/cases/{case["case_id"]}/lifecycle',json={'evidence_version':1,'lifecycle_revision':lifecycle['revision'],'action':'close','reason':'synthetic test'})
        assert close.status_code==200
        payload={'evidence_version':1,'request_id':uuid.uuid4().hex,'question':'새 질문','after_turn_id':None}
        assert c.post(f'/api/cases/{case["case_id"]}/conversation',json=payload).json()['error']=='CASE_CLOSED'
    from recase.conversation_store import create_turn
    store=Store(tmp_path/'pending.db');s=store.new_demo();case=store.cases(s['user_id'])[0]
    turn,_=create_turn(store,s['user_id'],case['id'],1,uuid.uuid4().hex,'대기 질문',None,{'backend':'fixture'})
    store.recover();assert store.job(s['user_id'],turn['id'])['error']=='SERVER_RESTARTED'


def test_history_limit_and_context_trimming_keep_whole_turns_and_all_current_sources(tmp_path):
    class Bounded(ChatModel):
        def fits_context(self,prompt,max_tokens):
            return len(json.loads(prompt.split('\nCONVERSATION_JSON=',1)[1])['previous_turns_untrusted'])<=1
    model=Bounded()
    with TestClient(app_at(tmp_path,model)) as c:
        case=enter(c);previous=None;completed=[]
        for index in range(4):
            turn,_=post(c,case,'후속 질문 '+str(index),previous);turn=wait_job(c,turn);completed.append(turn);previous=turn['id']
        answer=completed[-1]['result']['conversation']
        assert answer['history_turn_ids']==[completed[-2]['id']]
        assert answer['history_turns_omitted']==2
        prompt=json.loads(model.prompts[-1].split('\nCONVERSATION_JSON=',1)[1])
        assert len(prompt['evidence'])==len(case['evidence'])


def test_cursor_pages_keep_complete_history_and_owner_scoped_boundary(tmp_path):
    from recase.conversation_store import create_turn,list_turns
    store=Store(tmp_path/'pagination.db');s=store.new_demo();case,other=store.cases(s['user_id']);prior=None;ids=[]
    answer={'conversation':{'paragraphs':[],'missing_information':['합성 확인 사항']}}
    for index in range(23):
        turn,_=create_turn(store,s['user_id'],case['id'],1,uuid.uuid4().hex,'합성 질문 '+str(index),prior,{'backend':'fixture'})
        store.set_status(s['user_id'],turn['id'],'COMPLETED',result=answer);ids.append(turn['id']);prior=turn['id']
    page=list_turns(store,s['user_id'],case['id']);assert len(page['turns'])==20 and page['latest_turn_id']==ids[-1]
    older=list_turns(store,s['user_id'],case['id'],page['next_before'])
    assert [t['id'] for t in older['turns']]+[t['id'] for t in page['turns']]==ids
    assert older['next_before'] is None
    from recase.store import NotFound
    with pytest.raises(NotFound):list_turns(store,s['user_id'],other['id'],ids[0])


def test_case_deletion_and_latest_journal_replay_remove_conversation_in_old_copy(tmp_path):
    from recase.conversation_store import create_turn
    from recase.retention import delete_case,apply_deletions
    from recase.store import NotFound
    store=Store(tmp_path/'deletion.db');s=store.new_demo();case=store.cases(s['user_id'])[0]
    turn,_=create_turn(store,s['user_id'],case['id'],1,uuid.uuid4().hex,'SYNTHETIC_DELETE_THIS_QUESTION',None,{'backend':'fixture'})
    store.set_status(s['user_id'],turn['id'],'FAILED',error='SYNTHETIC_TEST')
    backup=store.backup(tmp_path/'pre-delete.db');journal=tmp_path/'deletions.jsonl'
    assert delete_case(store.path,journal,s['user_id'],case['id'])['status']=='PASS'
    assert apply_deletions(backup,journal)['deleted_cases_replayed']==1
    for current in [store,Store(backup)]:
        with pytest.raises(NotFound):current.job(s['user_id'],turn['id'])
        with current.db() as db:assert db.execute('SELECT count(*) FROM events WHERE job_id=?',(turn['id'],)).fetchone()[0]==0
