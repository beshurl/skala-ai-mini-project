import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
import pytest
from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.session_store import SqliteSessionStore
from agent.settings import Settings
from tests.support import FixtureMCP, FixedRetriever


@pytest.fixture
def deps(tmp_path):
    store = SqliteSessionStore(tmp_path / "test.db")
    deps = SupervisorDeps(FastLLM("fake", 0), QualityLLM("fake", 0), FixtureMCP(), store, "v2", Settings(tool_timeout=.1), FixedRetriever())
    yield deps
    store.close()
