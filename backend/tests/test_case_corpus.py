"""Data audit and leakage tests on fictional records, without model invocation."""
import pytest

from recase.case_corpus import (
    base_record, duplicate_audit, eligibility_preflight, fbi_record, paragraph_text, prepare, timeline_input,
)
from recase.public_collection import PublicCollector, TextDocument, write_json


def fictional_record(key="x", text="A fictional source document."):
    return base_record(key, "family", "SYNTHETIC_TEST", {"sha256":"0"*64}, text)


def test_public_record_is_not_an_approval_or_accuracy_measurement():
    record = fictional_record()
    assert not record["human_reviewed"] and record["quarantine"]
    assert not record["service_import_allowed"] and not record["training_eligible"]
    result = eligibility_preflight([record])
    assert result["eligible_records"] == 0
    assert result["model_evaluation"] == "NOT_RUN"
    assert result["actual_case_accuracy"] == "NOT_MEASURED"
    record.update(human_reviewed=True, privacy_status="HUMAN_APPROVED", label_status="HUMAN_APPROVED",
                  purpose_approvals={"training":"APPROVED"})
    assert eligibility_preflight([record])["eligible_records"] == 0


def test_fbi_birth_and_images_not_replicated_and_captured_not_convicted():
    record = fbi_record({"uid":"synthetic", "title":"Fictional notice", "status":"captured",
                         "dates_of_birth_used":["1900-01-01"], "images":[{"original":"private-image"}]}, {})
    assert "1900" not in record["text"] and "private-image" not in record["text"]
    assert record["outcome_label"] is None
    assert record["source_status"] == "captured"


def test_missing_notice_uid_is_rejected():
    with pytest.raises(ValueError):
        fbi_record({"title":"not a stable record"}, {})


def test_navigation_and_related_stories_are_not_evidence():
    doc = TextDocument('<main><p>A fictional source paragraph long enough to retain as evidence.</p>'
                       '<div class="related-stories"><p>A different case was convicted later; unrelated.</p></div>'
                       '<nav><p>Navigation content must never be added to evidence.</p></nav></main>')
    assert paragraph_text(doc) == ["A fictional source paragraph long enough to retain as evidence."]


def test_backfilled_source_is_filtered_but_remains_ineligible():
    paragraphs = ["Updated April 25, 2018: an arrest has been reported.", "The original notice asks for information."]
    record = timeline_input("golden_pre_updated", paragraphs)
    assert "arrest" not in record["input_text"]
    assert record["removed_paragraphs"] == 1
    assert record["historical_snapshot_verified"] is False and record["eligible"] is False
    assert "outcome_label" not in record


@pytest.mark.parametrize("key", ["seale_verdict", "ricks_retrospective", "houston_retrospective", "dunes_identified"])
def test_outcomes_and_retrospectives_are_never_pre_outcome_inputs(key):
    assert timeline_input(key, ["A source already reports the outcome."]) is None


def test_exact_and_near_duplicate_candidates_are_found():
    text = " ".join(f"token{i}" for i in range(70))
    records = [fictional_record("one", text), fictional_record("two", text),
               fictional_record("three", text + " different ending")]
    audit = duplicate_audit(records)
    assert audit["exact_groups"] == [["one", "two"]]
    assert len(audit["near_pairs"]) == 2
    assert "human family review required" in audit["limitation"]


def test_generic_short_boilerplate_is_not_a_case_family():
    audit = duplicate_audit([fictional_record("one", "Contact us."), fictional_record("two", "Contact us.")])
    assert not audit["exact_groups"] and not audit["near_pairs"]


def test_preparation_separates_references_and_preserves_prior_version(tmp_path):
    import httpx
    import json
    root = tmp_path / "vault"
    collector = PublicCollector(root)
    data = b'<main><p>Updated April 25, 2018: an arrest has been reported.</p><p>The fictional original notice requests information about an unknown person.</p></main>'
    receipt = collector._save_response("https://www.fbi.gov/fictional-test", 1,
        httpx.Response(200, headers={"content-type":"text/html"}), data)
    write_json(root / "collection.json", {"fbi_pages":[], "fbi_reported_total_start":0,
        "sources":[{"id":"golden_pre_updated", "kind":"case_source", "url":receipt["url"], "receipt":receipt}], "failures":[]})
    summary = prepare(root)
    assert summary["historical_inputs_verified"] == 0 and summary["eligible_training_records"] == 0
    reference = json.loads((root / "evaluation/reference-proposals.jsonl").read_text())
    candidate = json.loads((root / "processed/timeline-input-candidates.jsonl").read_text())
    assert reference["proposed_reported_status"] == "ARREST_REPORTED"
    assert "proposed_reported_status" not in candidate and "arrest" not in candidate["input_text"]
    before = (root / "audit.json").read_bytes()
    with pytest.raises(FileExistsError):
        prepare(root)
    prepare(root, root / "versions/v2")
    assert (root / "audit.json").read_bytes() == before
    assert (root / "versions/v2/evaluation/preflight.json").exists()
