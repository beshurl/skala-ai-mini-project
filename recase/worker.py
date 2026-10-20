"""One bounded queue, one inference worker, token-level cancellation."""
import asyncio
import threading
from recase.graph import build_graph
from recase.store import TERMINAL


class Worker:
    def __init__(self, store, mcp, model, capacity=8, timeout=180):
        self.store, self.mcp, self.model = store, mcp, model
        self.queue = asyncio.Queue(maxsize=capacity)
        self.timeout = timeout
        self.active = {}
        self.task = None
        self.stopping = False

    def start(self):
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.stopping = True
        for flag in self.active.values():
            flag.set()
        # A running token loop observes cancellation before the worker exits.
        await self.queue.put(None)
        await self.task

    async def run(self):
        while True:
            queued = await self.queue.get()
            if queued is None:
                self.queue.task_done()
                return
            owner, job_id = queued
            flag = threading.Event()
            self.active[job_id] = flag
            timer = asyncio.get_running_loop().call_later(self.timeout, flag.set)
            try:
                job = self.store.job(owner, job_id, private=True)
                if job["status"] in TERMINAL:
                    continue
                if job["cancel_requested"] or self.stopping:
                    self.store.set_status(owner, job_id, "CANCELLED", error="CANCELLED")
                    continue
                self.store.set_status(owner, job_id, "RUNNING")
                result = await build_graph(self.store, self.mcp, self.model, flag).ainvoke({"job": job}, config={"recursion_limit": 8, "callbacks": []})
                current = self.store.job(owner, job_id)
                if flag.is_set():
                    self.store.set_status(owner, job_id, "CANCELLED" if current["cancel_requested"] else "FAILED", error="CANCELLED" if current["cancel_requested"] else "ANALYSIS_TIMEOUT")
                else:
                    partial = any(code in result["result"]["limitations"] for code in ("MODEL_OUTPUT_INVALID", "RETRIEVAL_INSUFFICIENT"))
                    self.store.set_status(owner, job_id, "PARTIAL" if partial else "COMPLETED", result=result["result"])
            except InterruptedError:
                current = self.store.job(owner, job_id)
                self.store.set_status(owner, job_id, "CANCELLED" if current["cancel_requested"] else "FAILED", error="CANCELLED" if current["cancel_requested"] else "ANALYSIS_TIMEOUT")
            except Exception as error:
                # Never serialize model output, evidence text, credentials or exception messages into logs.
                current = self.store.job(owner, job_id)
                if self.store.snapshot(owner, current["case_id"])["evidence_version"] != current["version"]:
                    self.store.set_status(owner, job_id, "STALE", error="EVIDENCE_VERSION_CHANGED")
                else:
                    code = "MCP_TOOL_FAILED" if isinstance(error, RuntimeError) and str(error) == "MCP_TOOL_FAILED" else "ANALYSIS_FAILED"
                    self.store.set_status(owner, job_id, "FAILED", error=code)
            finally:
                timer.cancel()
                self.active.pop(job_id, None)
                self.queue.task_done()

    def cancel(self, owner, job_id):
        self.store.cancel(owner, job_id)
        flag = self.active.get(job_id)
        if flag is not None:
            flag.set()
        elif self.store.job(owner, job_id)["status"] == "QUEUED":
            self.store.set_status(owner, job_id, "CANCELLED", error="CANCELLED")
