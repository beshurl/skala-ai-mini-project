"""Environment-backed policy. Threshold changes are auditable in reports."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT / "data"
    db_path: Path = field(default_factory=lambda: Path(os.getenv("SESSION_DB", str(ROOT / "session.db"))))
    tool_timeout: float = field(default_factory=lambda: float(os.getenv("TOOL_TIMEOUT_SECONDS", "8")))
    request_timeout: float = field(default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SECONDS", "180")))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "120")))
    max_attempts: int = 3
    investigation_budget: int = 4
    investigation_planner_timeout: float = 35.0
    rag_top_k: int = 3
    cpu_warning: float = 80.0
    memory_warning: float = 85.0
    cpu_delta_warning: float = 15.0
    memory_delta_warning: float = 10.0
    embedding_model: str = field(default_factory=lambda: os.getenv("RAG_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"))
    rag_backend: str = field(default_factory=lambda: os.getenv("RAG_BACKEND", "fastembed"))

    def thresholds(self):
        return {"cpu_warning": self.cpu_warning, "memory_warning": self.memory_warning,
                "cpu_delta_warning_pp": self.cpu_delta_warning,
                "memory_delta_warning_pp": self.memory_delta_warning}
