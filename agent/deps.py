"""Explicit dependencies shared by graph nodes and specialist subgraphs."""
from dataclasses import dataclass, field
from typing import Any
from .settings import Settings


@dataclass
class SupervisorDeps:
    fast_llm: Any
    quality_llm: Any
    mcp: Any
    session_store: Any
    version: str
    settings: Settings = field(default_factory=Settings)
    retriever: Any = None
