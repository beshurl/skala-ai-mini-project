"""Generation API compatibility without loading MLX, weights, or real data."""
import sys
import threading
from types import ModuleType, SimpleNamespace

import pytest

from recase.model import LocalModel, SYSTEM


class Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
        assert messages == [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "synthetic prompt"}]
        return "synthetic formatted prompt"

    def encode(self, text):
        return [1] * 10


def model_and_calls(monkeypatch):
    calls = []
    mx = ModuleType("mlx.core")
    mx.random = SimpleNamespace(seed=lambda value: calls.append(("seed", value)))
    mx.get_peak_memory = lambda: 0
    mlx = ModuleType("mlx")
    mlx.core = mx
    ml = ModuleType("mlx_lm")
    def generate(*args, **kwargs):
        calls.append(("generation", kwargs))
        yield SimpleNamespace(text="{}", prompt_tokens=10, generation_tokens=1)
    ml.stream_generate = generate
    sampler = ModuleType("mlx_lm.sample_utils")
    sampler.make_sampler = lambda **kwargs: kwargs
    for name, module in [("mlx", mlx), ("mlx.core", mx), ("mlx_lm", ml), ("mlx_lm.sample_utils", sampler)]:
        monkeypatch.setitem(sys.modules, name, module)
    model = LocalModel.__new__(LocalModel)
    model.lock = threading.Lock()
    model.tokenizer = Tokenizer()
    model.model = object()
    model.load = lambda: None
    model.max_tokens = 256
    return model, calls


def test_legacy_default_and_explicit_nli_generation_remain_unchanged(monkeypatch):
    model, calls = model_and_calls(monkeypatch)
    assert model.infer("synthetic prompt")["generation_max_tokens"] == 256
    model.max_tokens = 64  # Predeclared NLI evaluation constructor parameter.
    assert model.infer("synthetic prompt")["generation_max_tokens"] == 64
    assert [c[1]["max_tokens"] for c in calls if c[0] == "generation"] == [256, 64]


def test_general_override_does_not_change_later_legacy_limits(monkeypatch):
    model, calls = model_and_calls(monkeypatch)
    assert model.infer("synthetic prompt", max_tokens=1024)["generation_max_tokens"] == 1024
    assert model.max_tokens == 256
    assert model.infer("synthetic prompt")["generation_max_tokens"] == 256
    assert all(c[1]["sampler"] == {"temp": 0} for c in calls if c[0] == "generation")


@pytest.mark.parametrize("value", [0, 1025, True, 64.0])
def test_invalid_override_never_generates(monkeypatch, value):
    model, calls = model_and_calls(monkeypatch)
    with pytest.raises(ValueError, match="GENERATION_LIMIT"):
        model.infer("synthetic prompt", max_tokens=value)
    assert not calls


def test_context_precheck_and_inference_share_budget(monkeypatch):
    model, calls = model_and_calls(monkeypatch)
    model.tokenizer.encode = lambda text: [1] * 4000
    assert not model.fits_context("synthetic prompt", 256)
    with pytest.raises(ValueError, match="CONTEXT_LIMIT"):
        model.infer("synthetic prompt")
    assert not [c for c in calls if c[0] == "generation"]
