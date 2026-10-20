import json
import pytest
from evaluation.scoring import LABELS, parse_response, score
from scripts.compare import compare, FIELDS


def gold():
    return [{"case_id": str(i), "label": label, "prompt": "E1: 공개 기록\nE2: 공개 진술"} for i, label in enumerate(LABELS)]


def response(label):
    return json.dumps({"label": label, "reason": "자료 관계를 확인함", "evidence_ids": ["E1", "E2"]})


def test_perfect_wrong_and_single_class():
    examples = gold()
    perfect = [{"case_id": e["case_id"], "response": response(e["label"])} for e in examples]
    m, _ = score(examples, perfect)
    assert m["accuracy"] == m["macro_f1"] == 1
    wrong = [{"case_id": str(i), "response": response(LABELS[(i + 1) % 3])} for i in range(3)]
    m, _ = score(examples, wrong)
    assert m["accuracy"] == m["macro_f1"] == 0
    m, _ = score(examples, [{"case_id": str(i), "response": response(LABELS[0])} for i in range(3)])
    assert m["accuracy"] == pytest.approx(1/3)
    assert m["macro_f1"] == pytest.approx(1/6)


@pytest.mark.parametrize("text", ["", "{", "[]", '{"label":"일치"}', '{"label":"일치","reason":"ok","evidence_ids":["SECRET"]}', '{"label":"일치","reason":"ok","evidence_ids":["E1","E1"]}', '{"label":"일치","reason":"ok","evidence_ids":[]}', '{"label":"일치","reason":"ok","evidence_ids":["E1"]'])
def test_invalid_contract(text):
    assert parse_response(text, {"E1", "E2"})[0] is None


def test_hidden_evidence_and_recovery():
    text = response("일치")
    assert parse_response(text, {"E1"})[1] == "inaccessible_evidence"
    wrapped = "```json\n" + text + "\n```"
    assert parse_response(wrapped, {"E1", "E2"})[0] is None
    assert parse_response(wrapped, {"E1", "E2"}, recover=True)[0]["label"] == "일치"


def test_missing_duplicate_and_mismatched_ids_stay_in_denominator():
    rows = [{"case_id": "0", "response": response("일치")}]
    m, scored = score(gold(), rows)
    assert m["count"] == 3 and m["accuracy"] == pytest.approx(1/3)
    assert scored[1]["error"] == "missing_prediction"
    m, scored = score(gold(), rows * 2 + [{"case_id": "other", "response": response("일치")}])
    assert m["accuracy"] == 0 and m["invalid_rate"] == 1
    assert m["integrity_errors"]["unexpected_ids"] == ["other"]
    assert scored[0]["error"] == "duplicate_prediction"


def test_gold_integrity():
    with pytest.raises(ValueError):
        score([], [])
    with pytest.raises(ValueError):
        score(gold() + gold(), [])


def test_comparison_rejects_legacy_and_changed_conditions():
    with pytest.raises(ValueError, match="UNVERIFIED"):
        compare({}, {})
    identity = {k: "same" for k in FIELDS}
    run = {"identity": identity, "accuracy": 1, "macro_f1": 1, "invalid_rate": 0, "mean_latency_s": 1}
    assert compare(run, run)["accuracy"]["delta"] == 0
    with pytest.raises(ValueError, match="revision"):
        compare(run, {**run, "identity": {**identity, "revision": "other"}})
