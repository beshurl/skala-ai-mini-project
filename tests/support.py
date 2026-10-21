"""Fixed read-only MCP adapter: deterministic fixtures, explicit failure injection."""
import json
from pathlib import Path
from mcp_server import SystemStatus

ROOT = Path(__file__).resolve().parents[1]


class FixtureMCP:
    def __init__(self, fail=None):
        self.calls = []
        self.reads = []
        self.fail = fail or set()

    async def call_tool(self, name, arguments, **kwargs):
        self.calls.append((name, dict(arguments)))
        target = arguments["system_name"]
        if (name, target) in self.fail:
            raise TimeoutError("fixture timeout")
        data = json.loads((ROOT / "data/monitoring.json").read_text())
        if target not in data:
            raise ValueError("미등록 시스템")
        if name == "get_monitoring_status":
            d = data[target]
            return SystemStatus(system_name=target, status=d["status"], cpu_percent=d["cpu_base"], memory_percent=d["memory_base"], alerts=d["alerts"], last_checked="2026-10-21T00:05:00Z").model_dump()
        if name == "get_recent_logs":
            logs = json.loads((ROOT / "data/logs.json").read_text())
            return {"system_name": target, "entries": logs["systems"][target], "data_kind": "synthetic"}
        if name == "get_deployment_snapshot":
            d = json.loads((ROOT / "data/snapshots.json").read_text())[arguments["scenario"]][arguments["phase"]].get(target)
            if d is None:
                raise ValueError("스냅샷 정보 부족")
            return d
        if name == "get_diagnostic_evidence":
            from agent.diagnostic_data import read_diagnostic_evidence
            return read_diagnostic_evidence(ROOT / "data", target, arguments["probe"], arguments["evidence_case"])
        raise ValueError("알 수 없는 도구")

    async def find_prompt(self, name):
        return "ops"

    async def get_prompt(self, name, arguments, **kwargs):
        return "고정 테스트 표준 절차: 선택 대상만 조회하고 근거를 검증한다."

    async def find_resource_template(self, name):
        return "ops", "runbook://incident-response/{incident_type}"

    async def read_resource(self, uri, **kwargs):
        self.reads.append(uri)
        return (ROOT / "data/runbooks" / (uri.rsplit("/", 1)[-1] + ".md")).read_text()


class FixedRetriever:
    """Unit tests replace inference, not production retrieval. Real RAG tested separately."""
    def search(self, query, top_k=3):
        ids = ["cpu-spike", "memory-leak", "network-timeout"]
        return [{"id": "R:" + i, "title": i, "uri": "runbook://incident-response/" + i,
                 "score": 0.8, "text": (ROOT / "data/runbooks" / (i + ".md")).read_text(), "model": "test-fixture"} for i in ids[:top_k]]
