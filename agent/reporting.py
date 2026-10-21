"""Fact-first report contract. The model selects grounded candidates, never invents metrics."""
import copy
import json
import hashlib
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable
from .comparison import assess, compare
from .prompts import REPORT_SYSTEM_PROMPT
from .contracts import ResponsePolicy

def canonical_report(state, settings):
    collected = state.get("collected", [])
    metrics = [c for c in collected if c["status"] == "completed" and c["source"] in ("monitoring", "snapshot")]
    docs = [c["data"] for c in collected if c["status"] == "completed" and c["source"] == "runbook"]
    logs = [c for c in collected if c["status"] == "completed" and c["source"] == "logs"]
    facts = [{"evidence_id": c["id"], "system_name": c["target"], "phase": c.get("phase"),
              **{k: c["data"][k] for k in ("status", "cpu_percent", "memory_percent", "alerts", "last_checked")},
              "verdict": assess(c["data"], settings)} for c in metrics]
    comparisons = []
    if state.get("mode") == "deployment":
        for target in state["targets"]:
            pair = {c["phase"]: c["data"] for c in metrics if c["target"] == target}
            comparisons.append({"system_name": target, **compare(pair.get("before"), pair.get("after"), settings)})
    hypotheses, actions = [], []
    policy_errors = []
    try:
        policies = json.loads((settings.data_dir / "response_policy.json").read_text(encoding="utf-8"))
        if not isinstance(policies, dict):
            raise ValueError("정책 목록 형식 오류")
    except (OSError, ValueError) as exc:
        policies = {}
        policy_errors.append("조치 정책을 읽지 못했습니다. 담당자가 정책 파일을 확인해야 합니다.")
    metric_ids = [f["evidence_id"] for f in facts]
    observed = [c["data"] for c in metrics if c.get("phase") != "before"]
    alerts_text = " ".join(a for m in observed for a in m.get("alerts", [])).lower()
    applicable = {
        "cpu-spike": any(m["cpu_percent"] >= settings.cpu_warning for m in observed),
        "memory-leak": any(m["memory_percent"] >= settings.memory_warning for m in observed),
        "high-latency": any(t in alerts_text for t in ("latency", "connection pool", "지연")),
        "network-timeout": any(t in alerts_text for t in ("timeout", "network", "packet loss")),
        "disk-full": "disk" in alerts_text,
        "db-down": any(m["status"] == "down" for m in observed),
    }
    if metric_ids:
        for d in docs:
            policy = policies.get(d["id"][2:])
            if policy and applicable.get(d["id"][2:], False):
                try:
                    policy = ResponsePolicy.model_validate(policy).model_dump()
                except Exception:
                    policy_errors.append(f"{d['id']}: 조치 정책 형식 오류입니다. 담당자 확인이 필요합니다.")
                    continue
                if hashlib.sha256(d["text"].strip().encode()).hexdigest() != policy.get("source_sha256"):
                    policy_errors.append(f"{d['id']}: 런북 원문이 변경되어 조건부 조치 정책 재검토가 필요합니다.")
                    continue
                refs = metric_ids + [c["id"] for c in logs if c["data"].get("entries")] + [d["id"]]
                hypotheses.append({"id": "H:" + d["id"][2:], "text": policy["hypothesis"], "evidence_ids": refs, "certainty": "추정"})
                actions.append({"id": "A:" + d["id"][2:], "text": policy["action"], "evidence_ids": refs, "condition": "Runbook의 적용 조건을 추가 확인한 뒤 담당자 승인 필요", "executed": False})
    investigation = state.get("investigation")
    if investigation and investigation.get("hypotheses"):
        # A generic CPU explanation cannot override actual tests of its competing causes.
        hypotheses = [h for h in hypotheses if h["id"] != "H:cpu-spike"]
        for h in investigation["hypotheses"]:
            if h["status"] in ("supported", "pending"):
                hypotheses.append({"id": h["id"], "text": f"{h['target']}: {h['title']} ({h['status_label']}). 인과관계 확정은 아닙니다.",
                    "evidence_ids": [h["observation_id"]] + [e["evidence_id"] for e in h["support"]], "certainty": "추정"})
        if investigation.get("stop_code") != "evidence_separated":
            actions = [a for a in actions if a["id"] != "A:cpu-spike"]
    failures = [{"id": c["id"], "target": c["target"], "source": c["source"], "error": c.get("error", "조회 실패")} for c in collected if c["status"] == "failed"]
    limitations = [f"{c['target']} ({c['source']}) 조회 실패: {c['error']}" for c in failures] + policy_errors
    if not facts:
        limitations.append("조회에 성공한 지표가 없어 시스템 정상 여부와 원인을 판단할 수 없습니다.")
    for target in state.get("targets", []):
        if not any(f["system_name"] == target for f in facts):
            limitations.append(f"{target}: 지표 정보 부족")
    if state.get("effective_query", state["query"]).strip().lower() in state.get("targets", []):
        limitations.append("구체적인 증상이 미제공되었습니다. 어떤 동작에서 문제가 발생했는지 알려주세요.")
    details = state.get("details", {})
    for key, label in (("onset", "발생 시각"), ("error_message", "오류 메시지")):
        if not details.get(key):
            limitations.append(f"{label} 미제공: 추가 입력이 필요합니다. 오류가 없으면 '없음'으로 입력하세요.")
    limitations.append("교육용 합성 관측입니다. 추가 조사의 5분 구간·CPU 기여 비중도 실제 운영 실측이 아니며 인과관계를 확정하지 않습니다.")
    if investigation and investigation.get("hypotheses"):
        limitations.append(investigation.get("stop_reason") or "추가 조사가 완료되지 않았습니다.")
        if investigation.get("stop_code") != "evidence_separated":
            limitations.append("가설을 충분히 구별하지 못해 CPU 원인별 조치 추천을 보류했습니다.")
    if docs:
        limitations.append("검색된 Runbook은 참고 후보입니다. 관측 조건이 맞는 문서만 권장 조치에 사용했습니다.")
    if not docs:
        limitations.append("참고 Runbook 정보 부족: 조건부 조치 추천을 생략했습니다.")
    verdicts = [f["verdict"] for f in facts] + [c["verdict"] for c in comparisons]
    unresolved = investigation and investigation.get("hypotheses") and investigation.get("stop_code") != "evidence_separated"
    verdict = "정보 부족" if failures or policy_errors or unresolved or not verdicts or "정보 부족" in verdicts else ("주의" if "주의" in verdicts else "정상")
    return {"title": "배포 전후 점검 보고서" if state.get("mode") == "deployment" else "인시던트 진단 보고서",
            "verdict": verdict, "targets": state.get("targets", []), "question": state.get("effective_query", state["query"]),
            "data_kind": "synthetic", "scenario": state.get("scenario", "stable"), "facts": facts,
            "logs": [{"evidence_id": c["id"], **c["data"]} for c in logs],
            "hypotheses": hypotheses, "recommendations": actions,
            "runbooks": docs, "comparisons": comparisons, "limitations": limitations,
            "failures": failures, "investigation": investigation, "thresholds": settings.thresholds(), "procedure": state.get("procedure", "기본 읽기 전용 진단 절차")}


def default_selection(report):
    return {"facts": copy.deepcopy(report["facts"]),
            "hypothesis_ids": [h["id"] for h in report["hypotheses"]],
            "action_ids": [a["id"] for a in report["recommendations"]]}

def apply_selection(report, selection):
    result = copy.deepcopy(report)
    result["hypotheses"] = [h for h in report["hypotheses"] if h["id"] in selection["hypothesis_ids"]]
    result["recommendations"] = [a for a in report["recommendations"] if a["id"] in selection["action_ids"]]
    return result


def render_report(report, passed=True):
    lines = [report["title"], f"판정: {report['verdict']} · 교육용 고정 샘플"]
    if not passed:
        lines += ["검증 미통과: 모델 초안을 제외하고 도구에서 확인 가능한 사실만 제공합니다."]
    lines += ["\n확인된 사실"]
    for f in report["facts"]:
        phase = f" ({f['phase']})" if f.get("phase") else ""
        lines += [f"- {f['system_name']}{phase}: {f['status']}, CPU {f['cpu_percent']}%, 메모리 {f['memory_percent']}%, 알림 {len(f['alerts'])}건 [{f['evidence_id']}]"]
    if not report["facts"]:
        lines += ["- 확인 가능한 지표가 없습니다."]
    for c in report["comparisons"]:
        lines += [f"- {c['system_name']}: {c['verdict']}, 전후 차이 {json.dumps(c['deltas'], ensure_ascii=False)} (CPU·메모리 단위: %p)"]
    if passed:
        lines += ["\n원인 추정"] + [f"- {h['text']} [{', '.join(h['evidence_ids'])}]" for h in report["hypotheses"]]
        lines += ["\n권장 조치"] + [f"- {a['text']} [{', '.join(a['evidence_ids'])}]" for a in report["recommendations"]]
    investigation = report.get("investigation")
    if investigation and investigation.get("hypotheses"):
        lines += ["\n반증 우선 추가 조사 · 관측 조건에 따른 판단"]
        for h in investigation["hypotheses"]:
            lines += [f"- {h['target']} / {h['title']}: {h['status_label']}"]
            for signal, label in (("support", "지지"), ("against", "반증"), ("unknown", "미확인")):
                lines += [f"  {label}: {e['detail']} [{e['evidence_id']}]" for e in h[signal]]
        for step in investigation["steps"]:
            lines += [f"- {step['round']}차 조사: {step['title']}. 이유: {step['reason']}", f"  사전 조건: {step['prediction']}"]
        lines += [f"- 종료: {investigation.get('stop_reason') or '조사 중단·미완료'}"]
    lines += ["\n추가 확인 필요"] + [f"- {s}" for s in report["limitations"]]
    lines += ["\n참고 출처"] + [f"- [{d['id']}] {d['title']} — {d['uri']}" for d in report["runbooks"]]
    return "\n".join(lines)


async def call_model(llm, system, user, schema=None):
    return await llm.achat(system, user, schema=schema)


@traceable(name="report.lcel_writer")
async def write_selection(llm, report, feedback=""):
    if hasattr(llm, "select_report"):
        return await llm.select_report(report, feedback)
    if not hasattr(llm, "achat"):
        return default_selection(report), {"tokens": 0, "usd": 0, "mode": "deterministic"}
    prompt = ChatPromptTemplate.from_messages([
        ("system", REPORT_SYSTEM_PROMPT),
        ("human", "보고서 근거와 후보:\n{evidence}\n검증 피드백:\n{feedback}")])
    usage = {}
    async def invoke(value):
        messages = value.to_messages()
        from .validation import DraftSelection
        schema = DraftSelection.model_json_schema()
        schema["properties"]["facts"].update({"minItems": len(report["facts"]), "maxItems": len(report["facts"])})
        text, measured = await call_model(llm, messages[0].content, messages[1].content, schema=schema)
        usage.update(measured)
        return text
    chain = prompt | RunnableLambda(invoke) | StrOutputParser()
    # The writer selects existing facts/candidates; it cannot alter the tested ledger.
    writer_evidence = {k: v for k, v in report.items() if k != "investigation"}
    text = await chain.ainvoke({"evidence": json.dumps(writer_evidence, ensure_ascii=False), "feedback": feedback})
    try:
        return json.loads(text), usage
    except json.JSONDecodeError:
        return {"unparsed": text[:1000]}, usage
