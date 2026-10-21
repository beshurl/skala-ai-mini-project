"""Read-only, explicitly synthetic observations behind the diagnostic MCP tool."""
import json
from .contracts import DiagnosticEvidence


def read_diagnostic_evidence(data_dir, target, probe, evidence_case):
    fixture = json.loads((data_dir / "investigation_cases.json").read_text(encoding="utf-8"))
    case = fixture["cases"][evidence_case]
    values = case["probes"].get(probe) if target == "payments-service" else None
    return DiagnosticEvidence(system_name=target, probe=probe, evidence_case=evidence_case,
        window_start=fixture["window_start"], window_end=fixture["window_end"], data_kind="synthetic",
        available=values is not None, values=values or {},
        missing_reason="" if values is not None else "해당 대상·시간 구간의 조사 자료가 제공되지 않았습니다.").model_dump()
