import copy
from dataclasses import replace

import pytest

from agent.graph import build_graph
from agent.investigation import validate_observation
from agent.diagnostic_data import read_diagnostic_evidence
from tests.test_workflows import initial


@pytest.mark.asyncio
@pytest.mark.parametrize("case,winner,stop,reads", [
    ("batch", "batch", "evidence_separated", 2),
    ("traffic", "traffic", "evidence_separated", 3),
    ("release", "release", "evidence_separated", 4),
    ("conflict", None, "conflicting_evidence", 4),
    ("missing", None, "evidence_exhausted", 4),
])
async def test_same_cpu_distinct_evidence_changes_conclusion(deps, case, winner, stop, reads):
    r = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 원인 진단", evidence_case=case))
    board = r["investigation"]
    assert r["report"]["facts"][0]["cpu_percent"] == 91
    assert board["stop_code"] == stop and board["used"] == reads
    supported = [h["kind"] for h in board["hypotheses"] if h["status"] == "supported"]
    assert supported == ([winner] if winner else [])
    if winner:
        assert any(h["id"].endswith(":"+winner) for h in r["report"]["hypotheses"])
    else:
        assert not r["report"]["recommendations"]
    assert len({s["probe_id"] for s in board["steps"]}) == reads
    assert all(s["prediction"] and s["otherwise"] and s["before"] for s in board["steps"])
    assert "H:cpu-spike" not in [h["id"] for h in r["report"]["hypotheses"]]


@pytest.mark.asyncio
async def test_precommitted_question_streams_before_observation(deps):
    events = []
    async for mode, payload in build_graph(deps).astream(initial("payments-service CPU 급증 진단"), stream_mode=["custom", "updates"]):
        if mode == "custom":
            events.append(payload)
    planned = [e for e in events if e["type"] == "ProbePlanned"]
    for p in planned:
        assert p["step"]["status"] == "planned" and not p["step"]["outcomes"]
        observed = next(e for e in events if e["type"] == "ProbeObserved" and e["step"]["probe_id"] == p["step"]["probe_id"])
        assert events.index(p) < events.index(observed)
    assert events[-1]["type"] == "InvestigationStopped"


@pytest.mark.asyncio
async def test_planner_invented_or_repeated_question_is_blocked(deps):
    class InvalidPlanner:
        async def select_probe(self, board, candidates):
            return {"probe_id": "unregistered-service/shell-command", "purpose": "fill_gap"}, {}
    deps.fast_llm = InvalidPlanner()
    r = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 진단"))
    assert r["investigation"]["stop_code"] == "planner_failed"
    assert not any(name == "get_diagnostic_evidence" for name, _ in deps.mcp.calls)
    assert r["report"]["facts"][0]["cpu_percent"] == 91
    assert not r["report"]["recommendations"]


@pytest.mark.asyncio
async def test_budget_does_not_turn_a_single_hint_into_a_confirmed_cause(deps):
    deps.settings = replace(deps.settings, investigation_budget=1)
    r = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 진단"))
    assert r["investigation"]["stop_code"] == "budget_exhausted"
    assert not any(h["status"] == "supported" for h in r["investigation"]["hypotheses"])
    assert r["investigation"]["used"] == 1
    assert not r["report"]["recommendations"]


@pytest.mark.asyncio
async def test_probe_failure_retains_original_facts_and_cannot_support_cause(deps):
    deps.mcp.fail = {("get_diagnostic_evidence", "payments-service")}
    r = await build_graph(deps).ainvoke(initial("payments-service CPU 급증 진단"))
    assert r["report"]["facts"][0]["cpu_percent"] == 91
    assert r["status"] == "partial"
    assert not r["report"]["hypotheses"] and not r["report"]["recommendations"]
    assert all(h["status"] == "inconclusive" for h in r["investigation"]["hypotheses"])


@pytest.mark.parametrize("mutation", ["target", "probe", "case", "stale", "future", "shape", "share"])
def test_mismatched_stale_or_malformed_observations_are_rejected(deps, mutation):
    step = {"target": "payments-service", "probe": "cpu-attribution"}
    raw = read_diagnostic_evidence(deps.settings.data_dir, "payments-service", "cpu-attribution", "batch")
    raw = copy.deepcopy(raw)
    if mutation == "target": raw["system_name"] = "web-01"
    if mutation == "probe": raw["probe"] = "job-window"
    if mutation == "case": raw["evidence_case"] = "traffic"
    if mutation == "stale": raw["window_end"] = "2026-10-20T00:05:00Z"
    if mutation == "future": raw["window_end"] = "2026-10-21T00:06:00Z"; raw["window_start"] = "2026-10-21T00:01:00Z"
    if mutation == "shape": raw["values"] = {"made_up": 100}
    if mutation == "share": raw["values"]["batch_cpu_share"] = 1
    with pytest.raises(ValueError):
        validate_observation(raw, step, "2026-10-21T00:05:00Z", "batch")


@pytest.mark.asyncio
async def test_retry_reuses_successful_probe_evidence(deps):
    graph = build_graph(deps)
    first = await graph.ainvoke(initial("payments-service CPU 급증 진단"))
    deps.mcp.calls.clear()
    second = await graph.ainvoke(initial("payments-service CPU 급증 진단", seed_collected=first["collected"]))
    assert not deps.mcp.calls
    assert all(s["reused"] for s in second["investigation"]["steps"])
