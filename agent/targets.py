"""Resolve only explicit catalog targets; clarification never changes the question."""
import json
import re
from pathlib import Path

SYSTEM_TOKEN = re.compile(r"(?<![\w-])[a-z][a-z0-9]*(?:-[a-z0-9]+)+(?![a-z0-9-])", re.I)
INCIDENT = re.compile(r"장애|진단|다운|지연|급증|오류|느[려리림]|안\s*(?:돼|되)|문제|점검|배포|모니터링|비교|상태|메모리|디스크|타임아웃|"
                      r"로그|원인|근거|가설|반증|조치|재시도|배치|트래픽|요청량|릴리스|응답|접속|끊[겨기김]|멈[춰추춤]|먹통|튕|반환|차오|"
                      r"(?<![a-z])(?:cpu|incident|timeout|error|exception|latency|memory|disk|traffic|deploy|crash|oom(?:killed)?)(?![a-z])|"
                      r"http\s*[45]\d\d|\b50[0234]\b", re.I)
# Short answers are meaningful only alongside an existing investigation or selected target.
FOLLOWUP_REPLY = re.compile(r"(?:(?:그럼|그러면|이어서|다시|계속|좀)\s*)*"
    r"(?:왜(?:요|죠|인가요|\s*그런가요)?|어떻게(?:요|하죠|\s*해야\s*(?:해요|하나요))?|다음은|그\s*다음|"
    r"없음|없어요|없습니다|모르겠어요|모릅니다|확인해\s*주세요|"
    r"(?:(?:오늘|어제)\s*)?(?:(?:오전|오후)\s*)?\d{1,2}(?::\d{2}|시(?:\s*\d{1,2}분)?)(?:\s*(?:부터|쯤|경))?)"
    r"[.!?~\s]*", re.I)


def catalog(data_dir: Path) -> dict:
    data = json.loads((data_dir / "monitoring.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("monitoring.json에 등록된 시스템이 없습니다.")
    return data


def explicit_targets(query: str, known: dict) -> tuple[list[str], list[str]]:
    tokens = [m.group().lower() for m in SYSTEM_TOKEN.finditer(query)]
    matched = [s for s in known if re.search(r"(?<![a-z0-9-])" + re.escape(s) + r"(?![a-z0-9-])", query, re.I)]
    matched.sort(key=lambda s: query.lower().index(s.lower()))
    unknown = [s for s in dict.fromkeys(tokens) if s not in known]
    return matched, unknown


def resolve_request(query: str, known: dict, context: dict, selected: list[str], mode: str) -> dict:
    targets, unknown = explicit_targets(query, known)
    unknown += [s for s in selected if s not in known]
    scope_conflict = bool(targets and selected and set(targets) != set(selected))
    targets = list(dict.fromkeys(targets + [s for s in selected if s in known]))
    pending = context.get("pending") or {}
    context_reply = bool(context.get("targets") and FOLLOWUP_REPLY.fullmatch(query))
    operational = bool(targets or unknown or selected or pending or context_reply or mode == "deployment" or INCIDENT.search(query) or (context.get("targets") and re.search(r"다시|그럼|이어서|어떻게|원인|로그", query)))
    if not operational:
        return {"route": "chat", "effective_query": query, "targets": [], "context": context}
    original = pending.get("query", query)
    effective = original if pending and query.strip() in targets else (f"{original}\n추가 정보: {query}" if pending else query)
    # A bare follow-up reuses the last explicit scope; a newly named scope replaces it.
    if not targets and not unknown and not pending and context.get("targets") and len(query) < 500:
        targets = context["targets"]
    is_followup = bool(context.get("targets") and not pending and (context_reply or re.search(r"다시|그럼|이어서|어떻게|오류 메시지|발생 시각", query)) and set(targets) == set(context.get("targets", [])))
    if is_followup:
        effective = context.get("original_question", context.get("last_question", query)) + "\n추가 질문: " + query
    new_context = dict(context)
    if unknown or not targets or scope_conflict:
        new_context["pending"] = {"query": effective, "mode": pending.get("mode", mode)}
        return {"route": "clarify", "targets": targets, "unknown_targets": list(dict.fromkeys(unknown)),
                "effective_query": effective, "context": new_context, "scope_conflict": scope_conflict}
    new_context.update({"pending": None, "targets": targets, "last_question": effective, "original_question": context.get("original_question", effective) if is_followup else effective})
    return {"route": "incident", "targets": targets, "unknown_targets": [],
            "effective_query": effective, "mode": pending.get("mode", mode), "context": new_context}
