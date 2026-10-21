"""Strict fact, source and allowed-action validation, independent of generation."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class ObservedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    system_name: str
    phase: str | None
    status: Literal["healthy", "degraded", "down"]
    cpu_percent: float
    memory_percent: float
    alerts: list[str]
    last_checked: str
    verdict: Literal["정상", "주의", "정보 부족"]


class DraftSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: list[ObservedFact] = Field(max_length=24)
    hypothesis_ids: list[str] = Field(max_length=6)
    action_ids: list[str] = Field(max_length=6)


def validate_selection(raw, report):
    errors = []
    try:
        obj = DraftSelection.model_validate(raw).model_dump()
    except Exception as exc:
        return [f"보고서 스키마 불일치: {str(exc)[:300]}"]
    if obj["facts"] != report["facts"]:
        errors.append("시스템명·수치·상태·알림·근거 ID가 조회 결과와 일치하지 않습니다.")
    for key, candidates in (("hypothesis_ids", report["hypotheses"]), ("action_ids", report["recommendations"])):
        allowed = {c["id"] for c in candidates}
        if any(v not in allowed for v in obj[key]) or len(set(obj[key])) != len(obj[key]):
            errors.append(f"{key}: 확인되지 않은 출처 또는 조치 조건입니다.")
        if allowed and not obj[key]:
            errors.append(f"{key}: 확인 가능한 가설/다음 행동이 누락되었습니다.")
    return errors
