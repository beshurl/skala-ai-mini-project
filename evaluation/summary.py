"""Present functional assertions and model grading separately without changing scores."""
import copy


def investigation_summary(summary):
    result = copy.deepcopy(summary)
    for row in result.get("cases", []):
        checks = row.get("checks", {})
        functional = [v for k, v in checks.items() if k != "judge_quality"]
        row["functional_passed"] = bool(functional) and all(functional)
    result["functional_passed"] = sum(r["functional_passed"] for r in result["cases"])
    result["judge_quality_passed"] = sum(r.get("checks", {}).get("judge_quality", False) for r in result["cases"])
    result["review_required"] = [r["id"] for r in result["cases"] if r["functional_passed"] and not r.get("checks", {}).get("judge_quality", False)]
    result["score_policy"] = "종합 통과는 기능 체크와 Judge 4점 이상을 모두 요구합니다. 기능 결과와 Judge 점수는 별도 표시하며 원래 점수와 통과 판정을 변경하지 않습니다."
    return result
