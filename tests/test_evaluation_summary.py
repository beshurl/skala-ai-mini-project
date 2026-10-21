from evaluation.summary import investigation_summary


def test_functional_success_never_changes_a_failed_judge_or_overall_verdict():
    original = {"passed": 0, "cases": [{"id": "case", "passed": False,
        "checks": {"same_cpu_preserved": True, "expected_conclusion": True, "judge_quality": False},
        "judge": {"scores": {"groundedness": 2}}}]}
    result = investigation_summary(original)
    assert result["functional_passed"] == 1 and result["judge_quality_passed"] == 0
    assert result["passed"] == 0 and result["cases"][0]["passed"] is False
    assert result["cases"][0]["judge"]["scores"]["groundedness"] == 2
    assert result["review_required"] == ["case"]
    assert "functional_passed" not in original
