"""One local MLX model per process, offline resolution and cancellation per token."""
import hashlib
import fcntl
import json
import os
import threading
import time
from pathlib import Path

MODEL_ID = "mlx-community/Qwen3-4B-4bit"
SYSTEM = "당신은 증거를 근거로 판단하며, 불충분한 증거에는 단정하지 않는 분석가입니다."
PROMPT_VERSION = "legacy-contract-thinking-off-v2"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_model(model=MODEL_ID):
    local = Path(model).expanduser()
    if local.is_dir():
        resolved = local.resolve()
    else:
        from huggingface_hub import snapshot_download
        resolved = Path(snapshot_download(model, local_files_only=True,
                                         allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])).resolve()
    config = json.loads((resolved / "config.json").read_text())
    if config.get("hidden_size") != 2560 or config.get("num_hidden_layers") != 36:
        raise ValueError("Expected Qwen3-4B architecture; refusing a different model")
    if config.get("quantization", {}).get("bits") != 4:
        raise ValueError("Expected 4-bit quantization")
    return resolved


class LocalModel:
    def __init__(self, model=MODEL_ID, adapter=None, max_tokens=256):
        os.environ["HF_HUB_OFFLINE"] = "1"
        self.path = resolve_model(model)
        self.adapter = Path(adapter).resolve() if adapter else None
        if self.adapter:
            cfg = json.loads((self.adapter / "adapter_config.json").read_text())
            if cfg.get("model") != MODEL_ID:
                raise ValueError("Adapter base model mismatch")
            if not (self.adapter / "adapters.safetensors").is_file():
                raise ValueError("Adapter weights missing")
        self.max_tokens = max_tokens
        self.lock = threading.Lock()
        self.model = self.tokenizer = None
        self.info = {"backend": "mlx", "model": MODEL_ID, "revision": self.path.name,
                     "config_sha256": sha256(self.path / "config.json"),
                     "tokenizer_sha256": sha256(self.path / "tokenizer.json"),
                     "quantization": {"bits": 4, "group_size": 64},
                     "adapter_sha256": sha256(self.adapter / "adapters.safetensors") if self.adapter else None,
                     "adapter_loaded": False, "lora_modules": 0,
                     "prompt_version": PROMPT_VERSION, "prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
                     "generation": {"temperature": 0, "max_tokens": max_tokens, "seed": 0, "thinking": False}}

    def load(self):
        if self.model is not None:
            return
        lock_path = Path(__file__).resolve().parents[1] / "runtime" / "model.lock"
        lock_path.parent.mkdir(exist_ok=True)
        self.process_lock = lock_path.open("a")
        try:
            fcntl.flock(self.process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.process_lock.close()
            raise RuntimeError("MODEL_BUSY: another training/inference process holds the local model lock") from None
        from mlx_lm import load
        self.model, self.tokenizer = load(str(self.path), adapter_path=str(self.adapter) if self.adapter else None)
        lora_count = sum("lora" in type(mod).__name__.lower() for _, mod in self.model.named_modules())
        if self.adapter and not lora_count:
            raise RuntimeError("Adapter requested but no LoRA modules loaded")
        self.info.update(adapter_loaded=bool(self.adapter and lora_count), lora_modules=lora_count)

    def close(self):
        self.model = self.tokenizer = None
        if hasattr(self, "process_lock"):
            self.process_lock.close()

    def infer(self, prompt, cancel=None):
        with self.lock:
            self.load()
            import mlx.core as mx
            from mlx_lm import stream_generate
            from mlx_lm.sample_utils import make_sampler
            mx.random.seed(0)
            formatted = self.tokenizer.apply_chat_template(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False)
            if len(self.tokenizer.encode(formatted)) + self.max_tokens > 4096:
                raise ValueError("CONTEXT_LIMIT")
            start = time.perf_counter()
            pieces, last = [], None
            for token in stream_generate(self.model, self.tokenizer, formatted, max_tokens=self.max_tokens, sampler=make_sampler(temp=0)):
                if cancel and cancel.is_set():
                    raise InterruptedError("CANCELLED")
                pieces.append(token.text)
                last = token
            return {"response": "".join(pieces), "seconds": time.perf_counter() - start,
                    "prompt_tokens": last.prompt_tokens if last else 0,
                    "generation_tokens": last.generation_tokens if last else 0,
                    "finish_reason": getattr(last, "finish_reason", None),
                    "peak_memory_gb": mx.get_peak_memory() / 1e9}
