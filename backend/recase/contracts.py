"""Public result contracts. No evaluation answers or model thought traces."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str
    quote: str = Field(min_length=1, max_length=1200)
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)


class GroundedNote(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=700)
    citations: list[Citation] = Field(min_length=1, max_length=6)


class ReviewHypothesis(GroundedNote):
    counter_citations: list[Citation] = Field(default_factory=list, max_length=6)
    reconsider_when: str = Field(min_length=1, max_length=400)
    status: Literal["UNVERIFIED"] = "UNVERIFIED"


class NextCheck(GroundedNote):
    purpose: str = Field(min_length=1, max_length=400)
    reconsider_when: str = Field(min_length=1, max_length=400)


class TimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    subject: str = Field(min_length=1, max_length=100)
    place: str = Field(min_length=1, max_length=100)
    at: str = Field(min_length=1, max_length=80)
    tolerance_seconds: float = Field(ge=0, le=86400)
    identity_verified: bool
    citations: list[Citation] = Field(min_length=1, max_length=3)


class TimeCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    first: TimeInput
    second: TimeInput
    minimum_travel_seconds: float | None = Field(default=None, ge=0, le=86400)
    travel_citations: list[Citation] = Field(default_factory=list, max_length=3)


class GeneralAssessment(BaseModel):
    """A model assessment, not verified truth or a hidden chain-of-thought."""
    model_config = ConfigDict(extra="forbid", strict=True)
    label: Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]
    rationale: str = Field(min_length=1, max_length=1600)
    citations: list[Citation] = Field(max_length=12)
    counter_citations: list[Citation] = Field(max_length=12)
    observations: list[GroundedNote] = Field(max_length=8)
    conflicts: list[GroundedNote] = Field(max_length=6)
    assumptions: list[str] = Field(max_length=6)
    missing_information: list[str] = Field(max_length=6)
    hypotheses: list[ReviewHypothesis] = Field(max_length=3)
    next_checks: list[NextCheck] = Field(max_length=6)
    time_checks: list[TimeCheck] = Field(default_factory=list, max_length=3)


class GeneralReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    observations: list[GroundedNote]
    conflicts: list[GroundedNote]
    hypotheses: list[ReviewHypothesis]
    next_checks: list[NextCheck]
    time_checks: list[dict]
    status: Literal["SOURCE_CHECKED_MODEL_ASSESSMENT", "INVALID", "BUDGET_BLOCKED", "NO_EVIDENCE"]


class ReasoningReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract: Literal["evidence-reasoning-v1"] = "evidence-reasoning-v1"
    scope: str = "공개 원문 인용과 형식 검사. 모델 해석의 사실성·추론 정확도는 별도 검증이 필요합니다."
    visible_evidence_count: int
    considered_evidence_ids: list[str]
    reviews: list[GeneralReview]
    model_calls_attempted: int
    prompt_sha256: list[str]
    generation_max_tokens: int = 1024
    plan: dict
    remaining_model_calls: int


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    label: Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]
    evidence_ids: list[str]
    rationale: str = Field(min_length=1, max_length=2000)
    missing_information: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    counter_citations: list[Citation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


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
    analysis_contract_version: str = "legacy-relation-v2"
    reasoning: ReasoningReport | None = None


class Relation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["일치", "모순", "추가확인필요"]
    reason: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str]
