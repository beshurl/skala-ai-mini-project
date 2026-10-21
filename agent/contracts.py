"""Shared typed MCP result contracts; malformed observations never become facts."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class SystemStatus(BaseModel):
    system_name: str
    status: Literal["healthy", "degraded", "down"]
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    last_checked: str
    alerts: list[str] = Field(default_factory=list, max_length=100)
    data_kind: str = "synthetic"


class LogEntry(BaseModel):
    time: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    message: str = Field(max_length=2000)


class LogResult(BaseModel):
    system_name: str
    entries: list[LogEntry] = Field(max_length=100)
    data_kind: str = "synthetic"


class ResponsePolicy(BaseModel):
    hypothesis: str = Field(min_length=1, max_length=2000)
    action: str = Field(min_length=1, max_length=2000)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DiagnosticEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system_name: str
    probe: Literal["job-window", "traffic-window", "release-window", "cpu-attribution"]
    evidence_case: Literal["batch", "traffic", "release", "conflict", "missing"]
    window_start: str
    window_end: str
    data_kind: Literal["synthetic"]
    available: bool
    values: dict
    missing_reason: str = ""
