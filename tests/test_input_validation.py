import pytest

from agent.input_validation import validate_input
from agent.targets import resolve_request
from server import ChatRequest


KNOWN = {"payments-service": {}, "auth-service": {}}
CONTEXT = {"targets": ["payments-service"], "original_question": "payments-service 응답이 느려요"}


@pytest.mark.parametrize("message", [
    "payments-service", "billing-service", "CPU가 급증했어요", "접속이 끊겨요", "OOMKilled",
    "쓰고 난 공간이 반환되지 않고 계속 차오릅니다", "HTTP 429", "응답이 없어요", "CPU 점검 예시를 써줘",
])
def test_operational_inputs_do_not_need_an_llm_for_admission(message):
    assert validate_input(message, KNOWN, {}, [])["passed"]


@pytest.mark.parametrize("message", ["왜?", "없음", "오전 9시", "그럼 다시 확인해주세요"])
def test_short_replies_require_context_and_keep_the_original_symptom(message):
    assert not validate_input(message, KNOWN, {}, [])["passed"]
    assert validate_input(message, KNOWN, CONTEXT, [])["passed"]
    result = resolve_request(message, KNOWN, CONTEXT, [], "helpdesk")
    assert result["route"] == "incident" and result["targets"] == ["payments-service"]
    assert CONTEXT["original_question"] in result["effective_query"]


def test_unicode_normalization_does_not_bypass_scope_or_content_checks():
    assert ChatRequest(message="\u200bＰＡＹＭＥＮＴＳ－ＳＥＲＶＩＣＥ\u200b").message == "PAYMENTS-SERVICE"
    assert not validate_input("\u200b\u2060", KNOWN, CONTEXT, ["payments-service"])["passed"]
    assert not validate_input("a" * 200 + " CPU", KNOWN, CONTEXT, ["payments-service"])["passed"]


def test_target_and_cpu_words_do_not_override_an_unrelated_writing_request():
    assert not validate_input("payments-service CPU에 대한 시를 써줘", KNOWN, CONTEXT, [])["passed"]
    assert not validate_input("payments-service 말고 오늘 날씨 알려줘", KNOWN, CONTEXT, [])["passed"]
