"""Service-owned persistent stdio session. Credentials never enter model input."""
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from recase.capability import mint
from recase.paths import BACKEND_ROOT


class EvidenceClient:
    def __init__(self, session, secret, observations=None):
        self.session, self.secret = session, secret
        self.lock = asyncio.Lock()
        self.observations = observations

    async def call(self, name, owner, case_id, version, **kwargs):
        args = {"case_id": case_id, "evidence_version": version, "access_token": mint(self.secret, owner, case_id, version), **kwargs}
        started, data, outcome = time.perf_counter(), {}, "SUCCESS"
        try:
            async with self.lock:
                result = await self.session.call_tool(name, args, read_timeout_seconds=timedelta(seconds=10))
            if result.isError:
                raise RuntimeError("MCP_TOOL_FAILED")
            data = result.structuredContent if result.structuredContent is not None else json.loads("".join(x.text for x in result.content if hasattr(x, "text")))
            if data.get("status") == "BLOCKED":
                outcome = "BLOCKED"
            return data
        except Exception:
            outcome = "ERROR"
            raise RuntimeError("MCP_TOOL_FAILED") from None
        finally:
            if self.observations:
                duration = (time.perf_counter()-started)*1000
                self.observations.record(component="mcp", event="mcp_call", operation=name, duration_ms=duration, outcome=outcome, error="MCP_TOOL_FAILED" if outcome == "ERROR" else None)
                if name == "search_case_evidence":
                    self.observations.record(component="rag", event="keyword_search", operation=name, duration_ms=duration, outcome=outcome,
                        error="MCP_TOOL_FAILED" if outcome == "ERROR" else None, documents=[{"id": hit.get("evidence_id"), "score": hit.get("score")} for hit in data.get("hits", [])])


@asynccontextmanager
async def connect(db_path, secret, observations=None):
    env = {"PATH": os.environ.get("PATH", ""), "RECASE_DB": str(db_path), "RECASE_MCP_SECRET": secret,
           "LANGCHAIN_TRACING_V2": "false", "LANGSMITH_TRACING": "false", "PYTHONUNBUFFERED": "1"}
    # Server configuration only; the model cannot choose corpus or review paths.
    for name in ("RECASE_REFERENCE_CORPUS", "RECASE_REFERENCE_REVIEWS"):
        if os.environ.get(name):
            env[name] = str(Path(os.environ[name]).resolve())
    params = StdioServerParameters(command=sys.executable, args=["-m", "recase.mcp_server"], cwd=str(BACKEND_ROOT), env=env)
    async with stdio_client(params) as streams:
        async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=10)) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            if names != {"get_public_case", "read_evidence", "search_case_evidence", "search_reference_judgments"}:
                raise RuntimeError("MCP_CAPABILITY_MISMATCH")
            yield EvidenceClient(session, secret, observations)
