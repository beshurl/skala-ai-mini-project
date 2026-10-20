"""Explicit fixture backend for tests. Never used as a real-model fallback."""
import json
import time
from recase.model import PROMPT_VERSION


class FixtureModel:
    def __init__(self, delay=0, invalid=False):
        self.delay, self.invalid = delay, invalid
        self.info = {"backend": "fixture", "model": "deterministic-test-fixture", "revision": "v1", "adapter_loaded": False, "prompt_version": PROMPT_VERSION}

    def load(self):
        pass

    def close(self):
        pass

    def infer(self, prompt, cancel=None):
        for _ in range(int(self.delay / .01)):
            if cancel and cancel.is_set():
                raise InterruptedError("CANCELLED")
            time.sleep(.01)
        text = "invalid" if self.invalid else json.dumps({"label": "모순" if "본인 확인이 완료된" in prompt else "추가확인필요", "reason": "합성 테스트 기록 관계입니다.", "evidence_ids": ["E1", "E2"]}, ensure_ascii=False)
        return {"response": text, "seconds": self.delay, "prompt_tokens": 0, "generation_tokens": 0}
