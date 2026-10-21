"""Automated review flags are candidates, not human approvals."""
from scripts.audit_external_review import digest, flags_for_item


def item(task="nli", target=None):
    subject = {"input": {"task": task, "prompt": "fixture"}, "answer": {"target": target or {"label": "neutral"}}}
    return {"subject": subject, "subject_sha256": digest(subject)}


def test_privacy_scan_includes_target_not_just_input():
    row = item("summary", {"summary": "연락처 010-1234-5678"})
    assert "PRIVACY_PATTERN_PHONE" in flags_for_item(row)


def test_auxiliary_vote_disagreement_is_flagged():
    native = {"gold_label": "neutral", "premise": "전제", "hypothesis": "가설", "label2": "contradiction", "label3": "contradiction", "label4": "contradiction", "label5": "neutral"}
    assert "UPSTREAM_AUXILIARY_MAJORITY_DISAGREES" in flags_for_item(item(), native)


def test_changed_subject_detected_without_approving_it():
    row = item()
    row["subject"]["input"]["prompt"] = "changed"
    assert "SUBJECT_HASH_CHANGED" in flags_for_item(row)
