"""Real asynchronous model calls with measured usage and LangSmith LLM spans."""
import os
import time
from collections import deque
from datetime import datetime, timezone

import httpx
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree


def _inputs(values):
    return {k: v for k, v in values.items() if k != "self"}


class LiveLLM:
    def __init__(self, provider, model, role, timeout=120, transport=None):
        if provider not in ("ollama", "openai"):
            raise ValueError("실제 모델 provider는 ollama 또는 openai여야 합니다.")
        self.provider, self.model, self.role = provider, model, role
        self.name = f"{provider}:{model}"
        self.timeout, self.transport = timeout, transport
        self.calls = deque(maxlen=256)
        self.responses = deque(maxlen=256)

    @traceable(name="llm.generate", run_type="llm", process_inputs=_inputs)
    async def _request(self, system, user, schema=None):
        run = get_current_run_tree()
        if run:
            run.metadata.update({"ls_provider": self.provider, "ls_model_name": self.model,
                                 "ls_model_type": "chat", "model_role": self.role})
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        payload = {"model": self.model, "messages": messages, "stream": False}
        headers = {}
        if self.provider == "ollama":
            url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
            payload.update({"think": False, "keep_alive": "30m", "options": {
                "temperature": 0, "num_ctx": int(os.getenv("OLLAMA_CONTEXT_LENGTH", "16384")),
                "num_predict": int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "4096"))}})
            if schema is not None:
                payload["format"] = schema
        else:
            key = os.getenv("OPENAI_API_KEY", "")
            if not key or key.endswith("..."):
                raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
            url = "https://api.openai.com/v1/chat/completions"
            headers["Authorization"] = "Bearer " + key
            payload.update({"temperature": 0, "max_completion_tokens": int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "4096"))})
            if schema is not None:
                payload["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        if self.provider == "ollama":
            text = data["message"]["content"]
            input_tokens, output_tokens = data.get("prompt_eval_count", 0), data.get("eval_count", 0)
            finish_reason = data.get("done_reason")
            request_id = None
            durations = {k: round(data.get(k, 0)/1_000_000, 3) for k in (
                "total_duration", "load_duration", "prompt_eval_duration", "eval_duration")}
        else:
            text = data["choices"][0]["message"].get("content")
            if not text:
                raise ValueError("모델이 응답을 거절했거나 출력이 비어 있습니다.")
            input_tokens = data.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = data.get("usage", {}).get("completion_tokens", 0)
            finish_reason = data["choices"][0].get("finish_reason")
            request_id, durations = data.get("id"), {}
        usage = {"model": self.model, "provider": self.provider, "role": self.role,
                 "input_tokens": input_tokens, "output_tokens": output_tokens,
                 "tokens": input_tokens + output_tokens, "elapsed_ms": round((time.perf_counter()-started)*1000, 2),
                 "finish_reason": finish_reason, "provider_request_id": request_id,
                 "provider_durations_ms": durations, "usd": 0.0,
                 "api_cost_usd": 0.0 if self.provider == "ollama" else None,
                 "cost_basis": "local inference; hardware cost excluded" if self.provider == "ollama" else "not calculated",
                 "measured": True, "created": datetime.now(timezone.utc).isoformat()}
        self.calls.append(dict(usage))
        self.responses.append({"text": text, "usage": dict(usage)})
        if finish_reason in ("length", "max_tokens"):
            raise ValueError("모델 출력 토큰 한도에 도달했습니다. 완성된 결과로 처리하지 않습니다.")
        return {"text": text, "model": self.model, "usage": usage,
                "usage_metadata": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                                   "total_tokens": input_tokens + output_tokens}}

    async def achat(self, system, user, schema=None):
        result = await self._request(system, user, schema)
        return result["text"], result["usage"]

def build_models(backend=None):
    backend = backend or os.getenv("LLM_BACKEND", "ollama")
    if backend == "fake":
        from .fake_llm import FastLLM, QualityLLM
        return backend, FastLLM("fast-model-stub", 0.00015), QualityLLM("quality-model-stub", 0.005)
    if backend not in ("ollama", "openai"):
        raise ValueError(f"지원하지 않는 LLM_BACKEND: {backend}")
    prefix = "OLLAMA" if backend == "ollama" else "OPENAI"
    default = "qwen3.5:2b" if backend == "ollama" else "gpt-4o-mini"
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    return backend, LiveLLM(backend, os.getenv(prefix+"_FAST_MODEL", default), "fast", timeout), LiveLLM(
        backend, os.getenv(prefix+"_QUALITY_MODEL", default), "writer", timeout)


def build_judge(backend=None):
    backend = backend or os.getenv("JUDGE_BACKEND", os.getenv("LLM_BACKEND", "ollama"))
    if backend not in ("ollama", "openai"):
        raise ValueError("Judge는 실제 ollama 또는 openai 모델로만 실행할 수 있습니다.")
    model = os.getenv("JUDGE_MODEL", "qwen3:8b" if backend == "ollama" else "gpt-4o")
    return LiveLLM(backend, model, "judge", float(os.getenv("JUDGE_TIMEOUT_SECONDS", "180")))
