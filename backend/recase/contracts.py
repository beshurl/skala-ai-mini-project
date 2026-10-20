"""Public result contracts. No evaluation answers or model thought traces."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    label: Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]
    evidence_ids: list[str]
    rationale: str = Field(min_length=1, max_length=2000)
    missing_information: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    evidence_version: int = Field(ge=1)
    findings: list[Finding]
    hypotheses: list[str] = Field(default_factory=list)
    limitations: list[str]
    model: dict
    usage: dict
    provenance: Literal["local_mlx", "deterministic_fixture"]


class Relation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["일치", "모순", "추가확인필요"]
    reason: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str]
