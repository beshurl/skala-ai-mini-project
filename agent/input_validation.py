"""Local input admission: no model, embedding, network call or history mutation."""
import re
import unicodedata

from .targets import INCIDENT, FOLLOWUP_REPLY, explicit_targets

UNRELATED_TASK = re.compile(
    r"(?<![가-힣a-z])(?:시|소설|동화|노래|가사|농담|유머)(?:를|을|좀|하나|한\s*편)?\s*"
    r"(?:써\s*줘|써주세요|지어\s*줘|지어주세요|만들어\s*줘|만들어주세요|해\s*줘|해주세요)[.!?~\s]*$|"
    r"(?:날씨|운세|로또(?:\s*번호)?|점심\s*메뉴|저녁\s*메뉴)(?:를|는|가|은|좀)?\s*"
    r"(?:알려\s*줘|알려주세요|추천해\s*줘|추천해주세요|어때|어때요|뽑아\s*줘)[.!?~\s]*$", re.I)


def normalize_message(message: str) -> str:
    text = unicodedata.normalize("NFKC", message)
    return "".join(c for c in text if unicodedata.category(c) != "Cf").strip()


def validate_input(message: str, known: dict, context: dict, selected: list[str]) -> dict:
    text = normalize_message(message)
    compact = re.sub(r"\s+", "", text).casefold()
    code, reason = "out_of_scope", "운영 장애 진단·배포 점검과 관련된 요청을 확인하지 못했습니다."
    if not re.search(r"[가-힣a-zA-Z0-9]", compact):
        code, reason = "no_content", "기호·이모지·자음만으로는 조사할 내용을 확인할 수 없습니다."
    elif re.fullmatch(r"(.{1,16}?)\1{3,}[.!?~]*", compact):
        code, reason = "repetition", "같은 문자나 문구가 반복되어 조사할 내용을 확인할 수 없습니다."
    elif UNRELATED_TASK.search(text):
        code, reason = "out_of_scope", "창작·일상 질문은 운영 장애 진단 범위에 포함되지 않습니다."
    else:
        repeated = re.search(r"(.{1,16}?)\1{9,}", compact)
        if len(compact) >= 80 and repeated and len(repeated.group()) >= len(compact) * .6:
            code, reason = "repetition", "반복 문자가 입력의 대부분을 차지합니다. 증상만 간단히 작성해주세요."
        else:
            targets, unknown = explicit_targets(text, known)
            if targets or unknown or INCIDENT.search(text):
                return {"passed": True, "code": "operational", "method": "local-rules"}
            if (context.get("pending") or context.get("targets") or selected) and FOLLOWUP_REPLY.fullmatch(text):
                return {"passed": True, "code": "context_reply", "method": "local-rules"}
    return {"passed": False, "code": code, "method": "local-rules", "reason": reason,
            "message": reason + "\n증상이나 시스템명을 입력해주세요. 예: payments-service 응답이 느려요."
                       "\nLLM 호출 없이 거절했습니다. 사용 토큰: 0"}
