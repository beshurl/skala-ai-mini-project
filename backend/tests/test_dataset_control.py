import copy
import json
import subprocess
import sys

import pytest

from recase.dataset_control import audit, latest_reviews, permitted, signature, subject_hash
from recase.ledger import append_record, read_ledger
from recase.paths import BACKEND_ROOT


def sample(sid, split="train", text=None):
    return {"sample_id": sid, "split": split, "prompt": text or f"서로 다른 문서의 검증에 필요한 고유한 내용 {sid}",
            **{key: sid for key in ("case_family", "document_family", "scenario_family", "template_family")},
            "label": "추가확인필요", "rights_basis": "synthetic unit test only", "source_type": "synthetic_fixture",
            "permissions": {key: True for key in ("processing", "training", "rag", "display", "redistribution")}}


def attestation(row):
    # Explicit test fixture. Never written to a project/data review ledger.
    return {"action": "approve", "actor_kind": "human_attestation", "subject_sha256": subject_hash(row),
            "reviewer": "test-human-fixture", "reviewed_at": "2026-10-20T00:00:00Z",
            "privacy_checked": True, "labels_checked": True, "permissions": row["permissions"]}


def test_review_binds_content_labels_rights_and_separate_purposes(tmp_path):
    row = sample("A")
    review = attestation(row)
    assert permitted(row, "training", review)
    for field, value in (("prompt", "changed"), ("label", "모순"), ("rights_basis", "new basis")):
        assert not permitted({**row, field: value}, "training", review)
    separate = copy.deepcopy(review)
    separate["permissions"]["display"] = False
    assert not permitted(row, "display", separate)
    assert not permitted(row, "evaluation", {**review, "labels_checked": False})
    assert not permitted(row, "rag", {**review, "privacy_checked": False})
    path = tmp_path / "reviews.jsonl"
    append_record(path, review)
    append_record(path, {"action": "revoke", "subject_sha256": subject_hash(row)})
    assert not permitted(row, "training", latest_reviews(path)[subject_hash(row)])


def test_family_components_are_transitive_across_splits():
    rows = [sample("A", text="개별 창고 계약서의 인계 기록을 확인합니다."),
            sample("B", text="완전히 다른 배송 내역의 손상을 기록했습니다."),
            sample("C", "final", text="별도의 대조표에서 식별자 불명인 항목을 조사합니다.")]
    rows[1]["document_family"] = rows[0]["document_family"]
    rows[2]["scenario_family"] = rows[1]["scenario_family"]
    report = audit(rows, [], {subject_hash(r): attestation(r) for r in rows}, True)
    assert report["status"] == "BLOCKED"
    assert report["connected_families"] == [["A", "B", "C"]]
    assert report["issue_counts"]["CROSS_SPLIT_FAMILY_OR_DUPLICATE"] >= 1


def test_near_duplicate_and_number_templates_detected_without_text_in_report():
    text = "인물 가나다의 기록은 서명 검증을 거쳤으며 같은 전송 식별자와 출처가 기록되어 있습니다. 시각은 19시입니다."
    rows = [sample("A", text=text), sample("B", "validation", text=text.replace("19", "20")),
            sample("C", "final", text=text.replace("19시", "19시 3분"))]
    report = audit(rows, [], history_complete=True)
    reasons = {reason for edge in report["conflicts"] for reason in edge["reasons"]}
    assert "numeric_template" in reasons and "near_trigram" in reasons
    assert text not in json.dumps(report, ensure_ascii=False)


def test_old_training_blocks_validation_and_all_old_exposure_blocks_final():
    old = sample("OLD", text="서명된 기록의 날짜와 장소를 대조하여 기재 오류 여부를 확인한다.")
    new = {**old, "sample_id": "NEW", "split": "validation"}
    history = [{"signature": signature(old), "purpose": "training"}]
    assert audit([new], history, history_complete=True)["issue_counts"]["PRIOR_EXPOSURE"] == 1
    history[0]["purpose"] = "development_authoring"
    assert "PRIOR_EXPOSURE" not in audit([new], history, history_complete=True)["issue_counts"]
    new["split"] = "final"
    assert audit([new], history, history_complete=True)["issue_counts"]["PRIOR_EXPOSURE"] == 1


def test_ledger_tampering_and_noninteractive_review_are_rejected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append_record(path, {"value": 1})
    path.write_text(path.read_text().replace('"value": 1', '"value": 2'))
    with pytest.raises(ValueError, match="integrity"):
        read_ledger(path)
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(json.dumps(sample("A")))
    result = subprocess.run([sys.executable, str(BACKEND_ROOT / "scripts" / "dataset_control.py"), "review", "--candidates", str(candidates),
                             "--sample-id", "A", "--reviews", str(tmp_path / "reviews.jsonl")], capture_output=True)
    assert result.returncode != 0
    assert not (tmp_path / "reviews.jsonl").exists()


def test_isolation_probe_does_not_mistake_sudo_failure_for_file_denial(monkeypatch):
    from scripts.verify_os_isolation import probe
    from types import SimpleNamespace
    monkeypatch.setattr("scripts.verify_os_isolation.pwd.getpwnam", lambda _: SimpleNamespace(pw_uid=999))
    monkeypatch.setattr("scripts.verify_os_isolation.subprocess.run", lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    result = probe("other-test-user", "/fake/answers", "open")
    assert result["probe_executed"] is False and "errno" not in result


def test_reviewed_disjoint_fixture_can_pass_but_changed_label_is_rejected():
    rows = [sample("one", text="E1: 항구의 물품 인계에서 확인된 서명자를 검사한다."),
            sample("two", "validation", text="E1: 다른 연도에 도서 발송 영수증의 수정 이력을 정리했다.")]
    for row in rows:
        row["answer"] = json.dumps({"label": "추가확인필요", "reason": "synthetic test rationale", "evidence_ids": ["E1"]})
    reviews = {subject_hash(row): attestation(row) for row in rows}
    assert audit(rows, [], reviews, True)["status"] == "PASS"
    rows[1]["label"] = "모순"
    report = audit(rows, [], reviews, True)
    assert report["issue_counts"]["INVALID_TARGET_CONTRACT_OR_LABEL"] == 1
    assert report["issue_counts"]["HUMAN_REVIEW_OR_PURPOSE_APPROVAL_REQUIRED"] == 1
