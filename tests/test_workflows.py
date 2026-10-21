import copy
import pytest
from agent.graph import build_graph
from agent.reporting import default_selection
from agent.comparison import compare, assess
from agent.targets import resolve_request, catalog, explicit_targets
from agent.session_store import SqliteSessionStore
from agent.settings import Settings


def initial(query, **kwargs):
    return {"query": query, "thread_id": "test", "history": [], "context": {}, "events": [], "mode": "helpdesk", **kwargs}


@pytest.mark.asyncio
async def test_ambiguous_then_resume_preserves_original_question(deps):
    graph = build_graph(deps)
    first = await graph.ainvoke(initial("CPU가 갑자기 올라가고 응답이 느려요"))
    assert first["route"] == "clarify"
    assert not deps.mcp.calls
    second = await graph.ainvoke(initial("payments-service", context=first["context"]))
    assert "CPU가 갑자기" in second["effective_query"]
    assert second["targets"] == ["payments-service"]
    assert {a["system_name"] for _, a in deps.mcp.calls} == {"payments-service"}
    assert second["report"]["facts"][0]["cpu_percent"] == 91


@pytest.mark.asyncio
async def test_unknown_never_falls_back(deps):
    result = await build_graph(deps).ainvoke(initial("billing-service 장애 진단"))
    assert result["route"] == "clarify"
    assert "미등록" in result["final"]
    assert not deps.mcp.calls


@pytest.mark.asyncio
async def test_every_explicit_target_and_no_extra(deps):
    r = await build_graph(deps).ainvoke(initial("payments-service와 web-01 장애 진단"))
    assert {f["system_name"] for f in r["report"]["facts"]} == {"payments-service", "web-01"}
    assert {a["system_name"] for _, a in deps.mcp.calls} == {"payments-service", "web-01"}


@pytest.mark.asyncio
async def test_partial_failure_retains_success_and_retries_only_failure(deps):
    deps.mcp.fail = {("get_monitoring_status", "web-01")}
    graph = build_graph(deps)
    first = await graph.ainvoke(initial("payments-service와 web-01 장애 진단"))
    assert first["status"] == "partial"
    assert first["report"]["verdict"] == "정보 부족"
    assert first["report"]["facts"][0]["system_name"] == "payments-service"
    assert any(c["source"] == "monitoring" for c in first["report"]["failures"])
    success = [c for c in first["collected"] if c["status"] == "completed"]
    deps.mcp.fail.clear(); deps.mcp.calls.clear(); deps.mcp.reads.clear()
    second = await graph.ainvoke(initial("payments-service와 web-01 장애 진단", seed_collected=success))
    assert deps.mcp.calls == [("get_monitoring_status", {"system_name": "web-01"})]
    assert deps.mcp.reads == []
    assert second["report"]["facts"][0] == first["report"]["facts"][0]
    assert second["status"] == "completed"


class WrongWriter:
    async def select_report(self, report, feedback):
        draft = default_selection(report)
        draft["facts"][0]["cpu_percent"] = 39
        return draft, {}


@pytest.mark.asyncio
async def test_wrong_cpu_blocked_after_three_attempts(deps):
    deps.quality_llm = WrongWriter()
    result = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 진단"))
    assert result["validation_attempts"] == 3
    assert not result["validation"]["passed"]
    assert result["status"] == "validation_failed"
    assert "CPU 91.0%" in result["final"] and "CPU 39" not in result["final"]
    assert result["report"]["recommendations"] == []
    assert "검증 미통과" in result["final"]


@pytest.mark.asyncio
async def test_invalid_first_draft_is_rewritten(deps):
    class RepairWriter:
        calls = 0
        async def select_report(self, report, feedback):
            self.calls += 1
            draft = default_selection(report)
            if self.calls == 1:
                draft["action_ids"] = ["A:unregistered"]
            else:
                assert "출처" in feedback
            return draft, {}
    deps.quality_llm = RepairWriter()
    r = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 진단"))
    assert r["validation"]["passed"] and r["validation"]["rewrites"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,verdict,cpu", [("stable", "정상", 0), ("cpu-rise", "주의", 57), ("new-alert", "주의", 0), ("missing-after", "정보 부족", None)])
async def test_deployment_scenarios(deps, scenario, verdict, cpu):
    r = await build_graph(deps).ainvoke(initial("web-01 배포 점검", mode="deployment", scenario=scenario))
    c = r["report"]["comparisons"][0]
    assert c["verdict"] == verdict
    assert c["deltas"].get("cpu_pp") == cpu
    assert not any(name == "get_monitoring_status" for name, _ in deps.mcp.calls)


def test_memory_restart_and_session_isolation(tmp_path):
    path = tmp_path / "persist.db"
    store = SqliteSessionStore(path)
    store.save_turn("a", "로그인 장애가 발생했어요", {"final":"대상을 선택해주세요", "status":"needs_clarification", "context":{"pending":{"query":"로그인 장애가 발생했어요"}}})
    store.close(); store = SqliteSessionStore(path)
    assert store.context("a")["pending"]["query"] == "로그인 장애가 발생했어요"
    assert store.load("b") == [] and store.records("b") == []
    assert len(store.load("a")) == 2
    store.close()


@pytest.mark.parametrize("cpu,memory,verdict", [(79.9,84.9,"정상"),(80,40,"주의"),(40,85,"주의")])
def test_threshold_boundaries(cpu, memory, verdict):
    assert assess({"status":"healthy","cpu_percent":cpu,"memory_percent":memory,"alerts":[]}, Settings()) == verdict


def test_target_boundary_no_substring(deps):
    known = catalog(deps.settings.data_dir)
    assert explicit_targets("payments-service-3 장애", known) == ([], ["payments-service-3"])
    assert explicit_targets("PAYMENTS-SERVICE 진단", known)[0] == ["payments-service"]


@pytest.mark.asyncio
async def test_all_metrics_failed_means_no_cause_or_action(deps):
    deps.mcp.fail = {("get_monitoring_status", "payments-service")}
    result = await build_graph(deps).ainvoke(initial("payments-service 장애 진단"))
    assert result["report"]["verdict"] == "정보 부족"
    assert not result["report"]["hypotheses"] and not result["report"]["recommendations"]


@pytest.mark.asyncio
async def test_followup_scope_does_not_add_unrequested_system(deps):
    context={"targets":["cache-service"],"last_question":"cache-service 메모리 장애"}
    r = await build_graph(deps).ainvoke(initial("오류 메시지는 없음. 다시 확인해주세요",context=context))
    assert r["targets"] == ["cache-service"]
    assert {a["system_name"] for _,a in deps.mcp.calls} == {"cache-service"}

@pytest.mark.asyncio
async def test_rag_failure_keeps_confirmed_metrics(deps):
    class BrokenIndex:
        def search(self,*args):raise RuntimeError('모델 준비 실패')
    deps.retriever=BrokenIndex()
    r=await build_graph(deps).ainvoke(initial('payments-service 장애 진단'))
    assert r['status']=='partial' and r['report']['facts'][0]['cpu_percent']==91
    assert r['report']['verdict']=='정보 부족'
    assert not r['report']['recommendations']
    assert any(f['source']=='runbook' for f in r['report']['failures'])


@pytest.mark.asyncio
async def test_details_survive_clarification_but_not_new_scope(deps):
    graph=build_graph(deps)
    first=await graph.ainvoke(initial('로그인 장애 진단',details={'onset':'오전 9시','error_message':'504'}))
    second=await graph.ainvoke(initial('auth-service',context=first['context']))
    assert second['details']['onset']=='오전 9시'
    third=await graph.ainvoke(initial('payments-service CPU 급증 진단',context=second['context']))
    assert third['details']=={}


@pytest.mark.asyncio
async def test_source_identity_mismatch_is_not_accepted(deps):
    original=deps.mcp.call_tool
    async def wrong(name,args):
        data=await original(name,args)
        if name=='get_monitoring_status':data['system_name']='web-01'
        return data
    deps.mcp.call_tool=wrong
    r=await build_graph(deps).ainvoke(initial('payments-service 장애 진단'))
    assert r['report']['verdict']=='정보 부족' and r['report']['facts']==[]


def test_numeric_and_evidence_contract_rejects_mutated_facts(deps):
    from agent.reporting import canonical_report
    from agent.validation import validate_selection
    report=canonical_report({'query':'test','targets':[],'collected':[]},deps.settings)
    draft=default_selection(report)
    draft['facts']=[{'system_name':'unregistered','cpu_percent':39}]
    assert validate_selection(draft,report)
    draft=default_selection(report);draft['hypothesis_ids']=['H:made-up']
    assert validate_selection(draft,report)

@pytest.mark.asyncio
async def test_conflicting_selected_and_named_scope_requires_confirmation(deps):
    r=await build_graph(deps).ainvoke(initial('payments-service 장애 진단',selected_targets=['auth-service']))
    assert r['route']=='clarify' and r['scope_conflict']
    assert not deps.mcp.calls


@pytest.mark.asyncio
async def test_followup_keeps_original_symptom_without_growing_history(deps):
    graph=build_graph(deps)
    r=await graph.ainvoke(initial('cache-service 메모리가 계속 차올라요. 장애 진단'))
    for _ in range(8):r=await graph.ainvoke(initial('그럼 다시 확인해주세요',context=r['context']))
    assert '메모리가 계속 차올라요' in r['effective_query']
    assert r['effective_query'].count('추가 질문:')==1


@pytest.mark.asyncio
async def test_clarification_retains_deployment_scenario(deps):
    graph=build_graph(deps)
    first=await graph.ainvoke(initial('배포 점검',mode='deployment',scenario='cpu-rise'))
    second=await graph.ainvoke(initial('web-01',context=first['context']))
    assert second['mode']=='deployment' and second['scenario']=='cpu-rise'
    assert second['report']['comparisons'][0]['deltas']['cpu_pp']==57


@pytest.mark.asyncio
async def test_runbook_policy_version_mismatch_suppresses_stale_advice(deps,tmp_path):
    import json
    from dataclasses import replace
    policies=json.loads((deps.settings.data_dir/'response_policy.json').read_text())
    policies['cpu-spike']['source_sha256']='0'*64
    (tmp_path/'response_policy.json').write_text(json.dumps(policies))
    (tmp_path/'monitoring.json').write_text((deps.settings.data_dir/'monitoring.json').read_text())
    deps.settings=replace(deps.settings,data_dir=tmp_path)
    r=await build_graph(deps).ainvoke(initial('payments-service CPU 급증 진단'))
    assert r['report']['facts'][0]['cpu_percent']==91
    assert not r['report']['recommendations']
    assert r['report']['verdict']=='정보 부족' and r['status']=='partial'
    assert any('정책 재검토' in s for s in r['report']['limitations'])
