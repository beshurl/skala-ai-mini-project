import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from agent.llm_runtime import LiveLLM, build_models, build_judge
from agent.judge import judge_evidence
from agent.judge import final_cause_claims
from agent.observability import verify_remote_run


@pytest.mark.asyncio
async def test_real_adapter_sends_schema_and_measures_provider_usage():
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    def respond(request):
        payload = json.loads(request.content)
        assert request.url.path == '/api/chat'
        assert payload['model'] == 'installed-model' and payload['think'] is False
        assert payload['format'] == schema and payload['stream'] is False
        return httpx.Response(200, json={"message": {"content": '{"ok":true}'}, "done_reason": "stop",
                                         "prompt_eval_count": 17, "eval_count": 6})
    model = LiveLLM('ollama', 'installed-model', 'writer', transport=httpx.MockTransport(respond))
    text, usage = await model.achat('system', 'question', schema)
    assert json.loads(text) == {'ok': True}
    assert usage['tokens'] == 23 and usage['input_tokens'] == 17
    assert usage['measured'] and usage['api_cost_usd'] == 0
    assert model.calls[0] == usage


@pytest.mark.asyncio
async def test_real_provider_failure_never_falls_back_to_fake():
    model = LiveLLM('ollama', 'missing-model', 'writer', transport=httpx.MockTransport(
        lambda _: httpx.Response(404, json={'error': 'model not found'})))
    with pytest.raises(httpx.HTTPStatusError):
        await model.achat('system', 'question')
    assert not model.responses


@pytest.mark.asyncio
async def test_truncated_output_is_recorded_but_rejected():
    model = LiveLLM('ollama', 'model', 'writer', transport=httpx.MockTransport(lambda _: httpx.Response(
        200, json={'message': {'content': '{'}, 'done_reason': 'length', 'eval_count': 1})))
    with pytest.raises(ValueError, match='토큰 한도'):
        await model.achat('system', 'question')
    assert model.calls[0]['tokens'] == 1


def test_actual_model_default_and_separate_judge(monkeypatch):
    monkeypatch.delenv('LLM_BACKEND', raising=False)
    monkeypatch.setenv('JUDGE_MODEL', 'independent-judge')
    backend, _, writer = build_models()
    assert backend == 'ollama' and isinstance(writer, LiveLLM)
    assert build_judge('ollama').model == 'independent-judge'
    with pytest.raises(ValueError):
        build_judge('fake')


def test_judge_receives_delivered_answer_and_original_evidence_only():
    result = {'query': 'q', 'final': 'CPU 39%', 'report': {'unused_hypotheses': ['secret candidate']},
              'collected': [{'id': 'm1', 'source': 'monitoring', 'status': 'completed', 'data': {'cpu_percent': 91}}]}
    payload = judge_evidence(result)
    assert payload['final_answer'] == 'CPU 39%'
    assert payload['evidence'][0]['data']['cpu_percent'] == 91
    assert 'secret candidate' not in json.dumps(payload)


def test_cause_audit_compares_delivered_claims_not_conditional_predictions():
    answer = ('확인된 사실\nCPU 91%\n원인 추정\n- 요청량 증가 가능성\n권장 조치\n추가 확인\n'
              '반증 우선 추가 조사 · 관측 조건에 따른 판단\n사전 조건: 중복 작업이면 배치 가설 지지\n'
              '최종 확정 결론: 배치가 원인으로 확정됨')
    assert final_cause_claims(answer) == ['- 요청량 증가 가능성','최종 확정 결론: 배치가 원인으로 확정됨']


@pytest.mark.asyncio
async def test_llm_detected_causal_contradiction_caps_score_without_overwriting_original(monkeypatch):
    import agent.judge as module
    answers = [json.dumps({k:5 for k in ('groundedness','numerical_accuracy','action_conditions','request_fulfillment','next_action')} | {'reason':'전체 평가'}),
               json.dumps({'contradicts_observations':True,'evidence_ids':['probe:one'],'reason':'관측에 반하는 원인 확정'})]
    async def call(*args,**kwargs): return answers.pop(0),{'tokens':1}
    monkeypatch.setattr(module,'call_model',call)
    result={'final':'원인 추정\n- 배치가 원인으로 확정됨\n권장 조치',
            'collected':[{'id':'probe:one','source':'diagnostic','status':'completed','data':{}}]}
    judged=await module.judge_report(result,SimpleNamespace(achat=True,name='judge-test'))
    assert judged['status']=='completed'
    assert judged['scores']['groundedness']==2 and judged['overall_scores']['groundedness']==5
    assert judged['claim_audit']['scores']['contradicts_observations']


@pytest.mark.asyncio
async def test_cause_audit_rejects_judge_invented_citation(monkeypatch):
    import agent.judge as module
    async def call(*args,**kwargs):
        return json.dumps({'contradicts_observations':False,'evidence_ids':['invented'],'reason':'unsupported'}),{}
    monkeypatch.setattr(module,'call_model',call)
    result={'final':'원인 추정\n- 조건부 가설\n권장 조치',
            'collected':[{'id':'probe:one','source':'diagnostic','status':'completed','data':{}}]}
    with pytest.raises(ValueError,match='제공되지 않은'):
        await module.audit_cause_claims(result,object())


@pytest.mark.asyncio
async def test_remote_readback_checks_route_specific_spans_and_feedback():
    llm = SimpleNamespace(name='llm.generate', run_type='llm', outputs={'usage_metadata': {'total_tokens': 23}}, child_runs=[])
    root = SimpleNamespace(name='evaluation.llm_as_judge', run_type='chain', child_runs=[llm],
                           end_time=True, error=None, session_id=uuid4(), outputs={})
    class Remote:
        saved = []
        def flush(self, **kwargs): pass
        def read_run(self, *args, **kwargs): return root
        def create_feedback(self, *args, **kwargs):
            assert kwargs['session_id'] == str(root.session_id)
            assert kwargs['score'] == 1
            item = SimpleNamespace(id=uuid4()); self.saved.append(item); return item
        def list_feedback(self, **kwargs): return self.saved
        def get_run_url(self, **kwargs): return 'https://smith.langchain.com/test'
    remote = Remote()
    clarified = await verify_remote_run(remote, uuid4(), 'test', {'groundedness': 5},
                                       {'llm.generate', 'evaluation.llm_as_judge'})
    assert clarified['verified'] and clarified['feedback_verified']
    missing = await verify_remote_run(remote, uuid4(), 'test')
    assert not missing['verified'] and 'metrics_specialist.collect' in missing['missing_spans']
