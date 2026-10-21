"""Local, bounded, metadata-only observations. No bodies, prompts, headers or paths."""
import contextvars
import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

request_context = contextvars.ContextVar("recase_request_id", default=None)
trace_context = contextvars.ContextVar("recase_trace_id", default=None)
TOOLS = frozenset({"get_public_case", "read_evidence", "search_case_evidence", "search_reference_judgments"})
COMPONENTS = frozenset({"http", "llm", "rag", "mcp", "system"})
EVENTS = frozenset({"request_finished", "model_inference", "model_loaded", "mcp_call", "keyword_search", "analysis_finished", "conversation_finished"})
OUTCOMES = frozenset({"SUCCESS", "ERROR", "CANCELLED", "BLOCKED", "INVALID"})
ERRORS = frozenset({"MODEL_LOAD_FAILED", "MODEL_INFERENCE_FAILED", "MCP_TOOL_FAILED", "MODEL_OUTPUT_INVALID", "RETRIEVAL_INSUFFICIENT", "GENERAL_OUTPUT_INVALID", "GENERAL_CONTEXT_LIMIT", "GENERAL_INPUT_BUDGET", "GENERAL_MODEL_FAILED", "CHAT_CONTEXT_LIMIT", "CHAT_INPUT_BUDGET", "CHAT_OUTPUT_INVALID", "CHAT_MODEL_FAILED", "ANALYSIS_FAILED", "ANALYSIS_TIMEOUT", "CANCELLED", "EVIDENCE_VERSION_CHANGED", "HTTP_INTERNAL_ERROR"})
ROUTES = frozenset({"/", "/health", "/ready", "/login", "/signup", "/api/auth/register", "/api/auth/login", "/api/auth/logout", "/api/auth/session", "/api/demo", "/api/practice", "/api/practice/general", "/api/session", "/api/demo/new", "/api/cases", "/api/cases/{case_id}", "/api/cases/{case_id}/lifecycle", "/api/cases/{case_id}/evidence/{evidence_id}", "/api/cases/{case_id}/release", "/api/cases/{case_id}/analyses", "/api/cases/{case_id}/conversation", "/api/jobs/{job_id}", "/api/jobs/{job_id}/cancel", "/api/jobs/{job_id}/events", "/api/cases/{case_id}/compare", "/api/admin/session", "/api/admin/summary", "/api/admin/logs", "SPA", "ASSET", "UNMATCHED"})


def identifier(value, pattern):
    return value if isinstance(value, str) and re.fullmatch(pattern, value) else None


def number(value):
    return float(value) if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


class Observations:
    def __init__(self, path, capacity=100_000):
        self.path, self.capacity, self.dropped = Path(path), capacity, 0
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("Observation database symlink refused")
        if not self.path.exists():
            self.path.touch(mode=0o600, exist_ok=False)
        self.path.chmod(0o600)
        with self.db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS observations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,created REAL NOT NULL,level TEXT NOT NULL,component TEXT NOT NULL,event TEXT NOT NULL,
                request_id TEXT,trace_id TEXT,operation TEXT,route TEXT,method TEXT,status INTEGER,duration_ms REAL NOT NULL,
                outcome TEXT NOT NULL,error TEXT,input_tokens INTEGER,output_tokens INTEGER,hit_count INTEGER,documents TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS observation_created ON observations(created);
                CREATE INDEX IF NOT EXISTS observation_request ON observations(request_id);
                CREATE INDEX IF NOT EXISTS observation_trace ON observations(trace_id);
            """)
            db.execute("INSERT OR IGNORE INTO metadata VALUES('started',?)", (time.time(),))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def record(self, *, component, event, duration_ms=0, outcome="SUCCESS", error=None, request_id=None, trace_id=None,
               operation=None, route=None, method=None, status=None, input_tokens=None, output_tokens=None, documents=None):
        # Explicit fields only. Arbitrary messages and exception strings have no storage slot.
        if component not in COMPONENTS or event not in EVENTS or outcome not in OUTCOMES:
            self.dropped += 1
            return
        error = error if error in ERRORS or isinstance(error, str) and re.fullmatch(r"HTTP_[1-5][0-9]{2}", error) else None
        documents = [{"id": d["id"], "score": number(d.get("score"))} for d in (documents or [])[:10]
                     if isinstance(d, dict) and identifier(d.get("id"), r"E-[a-f0-9]{16}") and number(d.get("score")) is not None]
        values = (time.time(), "ERROR" if outcome in {"ERROR", "INVALID"} else "WARN" if outcome in {"BLOCKED", "CANCELLED"} else "INFO",
                  component, event, identifier(request_id or request_context.get(), r"[a-f0-9]{32}"),
                  identifier(trace_id or trace_context.get(), r"JOB-[a-f0-9]{16}"), operation if operation in TOOLS | {"infer", "load", "analysis", "conversation"} else None,
                  route if route in ROUTES else None, method if method in {"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"} else None,
                  status if isinstance(status, int) and 100 <= status <= 599 else None, number(duration_ms) or 0, outcome, error,
                  int(input_tokens) if number(input_tokens) is not None else None, int(output_tokens) if number(output_tokens) is not None else None,
                  len(documents) if component == "rag" and outcome == "SUCCESS" else None, json.dumps(documents))
        try:
            with self.db() as db:
                db.execute("INSERT INTO observations(created,level,component,event,request_id,trace_id,operation,route,method,status,duration_ms,outcome,error,input_tokens,output_tokens,hit_count,documents) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
                db.execute("DELETE FROM observations WHERE id <= (SELECT coalesce(max(id),0)-? FROM observations)", (self.capacity,))
        except sqlite3.Error:
            # Observability failure does not change analysis results; explicitly visible to the operator.
            self.dropped += 1

    def logs(self, *, since, component="", level="", q="", request_id="", trace_id="", errors_only=False, limit=50, offset=0):
        where, args = ["created>=?"], [since]
        for key, value in (("component", component), ("level", level), ("request_id", request_id), ("trace_id", trace_id)):
            if value:
                where.append(key + "=?")
                args.append(value)
        if errors_only:
            where.append("outcome IN ('ERROR','INVALID')")
        if q:
            where.append("(event LIKE ? ESCAPE '\\' OR error LIKE ? ESCAPE '\\' OR operation LIKE ? ESCAPE '\\' OR route LIKE ? ESCAPE '\\')")
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            args += ["%" + escaped + "%"] * 4
        with self.db() as db:
            total = db.execute("SELECT count(*) FROM observations WHERE " + " AND ".join(where), args).fetchone()[0]
            rows = db.execute("SELECT * FROM observations WHERE " + " AND ".join(where) + " ORDER BY id DESC LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return {"items": [{**dict(r), "documents": json.loads(r["documents"])} for r in rows], "total": total, "limit": limit, "offset": offset}

    def summary(self, seconds):
        now = time.time()
        with self.db() as db:
            rows = [dict(r) for r in db.execute("SELECT created,component,event,operation,duration_ms,outcome,input_tokens,output_tokens,error FROM observations WHERE created>=?", (now - seconds,))]
            started = db.execute("SELECT value FROM metadata WHERE key='started'").fetchone()[0]
            retained, oldest = db.execute("SELECT count(*),min(created) FROM observations").fetchone()
        def metric(part):
            durations = sorted(r["duration_ms"] for r in part)
            def percentile(p):
                return durations[max(0, math.ceil(len(durations) * p) - 1)] if durations else None
            return {"count": len(part), "errors": sum(r["outcome"] in {"ERROR", "INVALID"} for r in part),
                          "success_rate": sum(r["outcome"] == "SUCCESS" for r in part) / len(part) if part else None,
                          "average_ms": sum(durations) / len(durations) if durations else None, "p50_ms": percentile(.5), "p95_ms": percentile(.95),
                          "input_tokens": sum(r["input_tokens"] for r in part if r["input_tokens"] is not None) if any(r["input_tokens"] is not None for r in part) else None,
                          "output_tokens": sum(r["output_tokens"] for r in part if r["output_tokens"] is not None) if any(r["output_tokens"] is not None for r in part) else None}
        metrics = {c: metric([r for r in rows if r["component"] == c]) for c in ("http", "llm", "rag", "mcp")}
        tool_metrics = {tool: metric([r for r in rows if r["component"] == "mcp" and r["operation"] == tool]) for tool in sorted(TOOLS)}
        width = seconds / 24
        buckets = [{"created": now - seconds + i * width, "count": 0, "errors": 0} for i in range(24)]
        groups = {}
        for r in rows:
            if r["component"] == "http":
                b = buckets[min(23, max(0, int((r["created"] - now + seconds) / width)))]
                b["count"] += 1
                b["errors"] += r["outcome"] == "ERROR"
            if r["error"] and r["outcome"] in {"ERROR", "INVALID"}:
                key = r["component"], r["error"]
                groups[key] = groups.get(key, 0) + 1
        return {"started": started, "retained": retained, "oldest": oldest, "dropped": self.dropped, "period_seconds": seconds, "metrics": metrics,
                "buckets": buckets, "tool_metrics": tool_metrics, "error_groups": [{"component": k[0], "error": k[1], "count": v} for k, v in sorted(groups.items(), key=lambda i: -i[1])]}


class ObservedModel:
    """Observe the exact model call in the worker without changing the serving singleton."""
    def __init__(self, model, observations):
        self.model, self.observations = model, observations

    @property
    def info(self):
        return self.model.info

    def fits_context(self, prompt, max_tokens):
        return self.model.fits_context(prompt, max_tokens) if hasattr(self.model, "fits_context") else True

    def infer(self, prompt, cancel=None, **kwargs):
        started, reply, outcome, error = time.perf_counter(), {}, "SUCCESS", None
        try:
            reply = self.model.infer(prompt, cancel, **kwargs)
            return reply
        except InterruptedError:
            outcome, error = "CANCELLED", "CANCELLED"
            raise
        except Exception:
            outcome, error = "ERROR", "MODEL_INFERENCE_FAILED"
            raise
        finally:
            self.observations.record(component="llm", event="model_inference", operation="infer", duration_ms=(time.perf_counter()-started)*1000,
                                     outcome=outcome, error=error, input_tokens=reply.get("prompt_tokens"), output_tokens=reply.get("generation_tokens"))
