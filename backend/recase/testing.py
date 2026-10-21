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

    def infer(self, prompt, cancel=None, *, max_tokens=None):
        for _ in range(int(self.delay / .01)):
            if cancel and cancel.is_set():
                raise InterruptedError("CANCELLED")
            time.sleep(.01)
        if "\nINPUT_JSON=" in prompt and not self.invalid:
            data = json.loads(prompt.split("\nINPUT_JSON=", 1)[1])
            evidence = data["evidence"]
            citations = [{"evidence_id":e["evidence_id"],"quote":e["text"][:100]} for e in evidence[:2]]
            text = json.dumps({"label":"INSUFFICIENT", "rationale":"합성 테스트용 응답입니다. 공개 원문 연결과 화면 흐름을 확인하며 실제 추론 성능을 나타내지 않습니다.",
                               "citations":citations,"counter_citations":[],
                               "observations":[{"text":"공개된 자료의 원문 구간입니다.","citations":citations}] if citations else [],
                               "conflicts":[],"assumptions":[],"missing_information":["실제 모델의 자료 해석과 독립 검증"],
                               "hypotheses":[{"text":"공개 자료의 신원·시점·출처를 더 확인할 필요가 있습니다.","citations":citations,"counter_citations":[],"reconsider_when":"원기록을 대조한 뒤 재검토","status":"UNVERIFIED"}] if citations else [],
                               "next_checks":[{"text":"원기록과 출처를 대조합니다.","citations":citations,"purpose":"자료의 정확성과 연결 범위를 확인하기 위해","reconsider_when":"추가 확인 자료가 확보되었을 때"}] if citations else []},ensure_ascii=False)
        else:
            text = "invalid" if self.invalid else json.dumps({"label": "모순" if "본인 확인이 완료된" in prompt else "추가확인필요", "reason": "합성 테스트 기록 관계입니다.", "evidence_ids": ["E1", "E2"]}, ensure_ascii=False)
        return {"response": text, "seconds": self.delay, "prompt_tokens": 0, "generation_tokens": 0}
