"""Read-only operational MCP: validated Tools, URI Resources and procedure Prompts.

Every shipped monitoring/log/snapshot value is labeled synthetic. No remediation tool.
"""
import json
from pathlib import Path
from typing import Literal
from fastmcp import FastMCP
from agent.contracts import SystemStatus
from agent.diagnostic_data import read_diagnostic_evidence

mcp = FastMCP(name="capstone-all-total-ops")
DATA_DIR = Path(__file__).resolve().parent / "data"


def _known(system_name):
    data = json.loads((DATA_DIR / "monitoring.json").read_text())
    if system_name not in data:
        raise ValueError(f"미등록 시스템: {system_name}")
    return data[system_name]


@mcp.tool()
def list_systems() -> dict:
    """monitoring.json에 등록된 시스템 이름만 반환합니다."""
    return {"systems": list(json.loads((DATA_DIR / "monitoring.json").read_text())), "data_kind": "synthetic"}


@mcp.tool()
def get_monitoring_status(system_name: str) -> SystemStatus:
    """고정 교육용 샘플을 조회합니다. 임의 jitter를 추가하지 않습니다."""
    data = _known(system_name)
    return SystemStatus(system_name=system_name, status=data["status"],
                        cpu_percent=data["cpu_base"], memory_percent=data["memory_base"],
                        alerts=data.get("alerts", []), last_checked="2026-10-21T00:05:00Z")


@mcp.tool()
def get_recent_logs(system_name: str) -> dict:
    """지정 대상의 교육용 로그를 조회합니다. 빈 로그는 원인 부재를 뜻하지 않습니다."""
    _known(system_name)
    data = json.loads((DATA_DIR / "logs.json").read_text())
    return {"system_name": system_name, "entries": data["systems"].get(system_name, []), "data_kind": "synthetic"}


@mcp.tool()
def get_diagnostic_evidence(system_name: str,
                            probe: Literal["job-window", "traffic-window", "release-window", "cpu-attribution"],
                            evidence_case: Literal["batch", "traffic", "release", "conflict", "missing"] = "batch") -> dict:
    """선택한 반증 질문의 5분 관측 근거를 읽습니다. 교육용 샘플이며 시스템을 변경하지 않습니다."""
    _known(system_name)
    return read_diagnostic_evidence(DATA_DIR, system_name, probe, evidence_case)


@mcp.tool()
def get_deployment_snapshot(system_name: str, scenario: Literal["stable", "cpu-rise", "new-alert", "missing-after"], phase: Literal["before", "after"]) -> dict:
    """격리된 전후 샘플을 읽습니다. 원본 monitoring.json은 변경하지 않습니다."""
    _known(system_name)
    data = json.loads((DATA_DIR / "snapshots.json").read_text())
    snapshot = data[scenario][phase].get(system_name)
    if snapshot is None:
        raise ValueError(f"{system_name}: {phase} 스냅샷 정보 부족")
    return snapshot


@mcp.resource("runbook://incident-response/{incident_type}")
def get_incident_runbook(incident_type: str) -> str:
    """화이트리스트 문서 ID만 허용하는 정적 Runbook Resource."""
    files = {p.stem: p for p in (DATA_DIR / "runbooks").glob("*.md")}
    if incident_type not in files:
        raise ValueError(f"등록되지 않은 Runbook: {incident_type}")
    return files[incident_type].read_text(encoding="utf-8")


@mcp.prompt()
def incident_analysis_prompt(system_name: str, symptom: str) -> str:
    """확정된 대상과 증상만 포함하는 공통 조사 절차."""
    return f"""시스템: {system_name}\n사용자 증상(사실로 간주하지 말 것): {symptom}
1. 확정된 대상만 조회하고 실패 항목을 격리한다.
2. 모니터링과 로그를 수집하고 증상 및 관측값으로 여러 Runbook을 의미 검색한다.
3. 관측 사실, 원인 가설, 조건부 권장 조치, 정보 부족과 근거 ID를 구분한다.
4. 시스템명·수치·출처·조치 조건 검증 실패 시 재작성하며 강제 통과하지 않는다.
"""


if __name__ == "__main__":
    mcp.run(show_banner=False)
