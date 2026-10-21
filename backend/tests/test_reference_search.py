import copy
import hashlib
import json
import os

import pytest

from recase.dataset_control import subject_hash
from recase.ledger import append_record
from recase.reference_search import ReferenceCorpus, citation_metrics, load_corpus, retrieval_metrics


def example():
    # Synthetic unit fixture only; never a production human-review record.
    text = "가상 판례는 연구실 기록의 출처 확인을 설명한다."
    doc = {"doc_id": "synthetic-reference", "source_type": "synthetic_fixture", "text": text,
           "clean_sha256": hashlib.sha256(text.encode()).hexdigest(), "rights_basis": "locally authored test fixture",
           "permissions": {"processing": True, "rag": True, "display": True, "training": False},
           "spans": [{"page": 1, "start": 0, "end": len(text), "text": text}]}
    review = {"action": "approve", "actor_kind": "human_attestation", "subject_sha256": subject_hash(doc),
              "reviewer": "synthetic-test-record-not-a-real-review", "reviewed_at": "fixture-only",
              "privacy_checked": True, "permissions": {"processing": True, "rag": True, "display": True}}
    return doc, review


def corpus():
    doc, review = example()
    return ReferenceCorpus([doc], {subject_hash(doc): review})


def test_rag_and_display_are_separate_required_approvals():
    doc, review = example()
    assert corpus().search("연구실")
    for place in (doc, review):
        original = place["permissions"]["display"]
        place["permissions"]["display"] = False
        with pytest.raises(PermissionError):
            ReferenceCorpus([doc], {subject_hash(doc): review})
        place["permissions"]["display"] = original
    assert not doc["permissions"]["training"]


def test_legacy_flags_revocation_and_changed_text_never_enter_search():
    doc, review = example()
    with pytest.raises(PermissionError):
        ReferenceCorpus([{**doc, "human_reviewed": True}], {})
    with pytest.raises(PermissionError):
        ReferenceCorpus([doc], {subject_hash(doc): {**review, "action": "revoke"}})
    changed = {**doc, "text": "다른 원문"}
    with pytest.raises(PermissionError):
        ReferenceCorpus([changed], {subject_hash(doc): review})
    with pytest.raises(ValueError, match="HASH"):
        ReferenceCorpus([changed], {subject_hash(changed): {**review, "subject_sha256": subject_hash(changed)}})


def test_unicode_offsets_and_wrong_source_quote_are_verified():
    current = corpus()
    hit = current.search("연구실")[0]
    assert current.valid_quote(hit) and hit["role"] == "context_not_current_case_evidence"
    assert hit["source_type"] == "synthetic_fixture"
    for wrong in ({**hit, "start": True}, {**hit, "quote": hit["quote"] + "가"},
                  {**hit, "document_id": "unapproved"}, {**hit, "document_id": []},
                  {**hit, "source_type": "actual_judgment"}, {**hit, "document_type": "case_evidence"}):
        assert not current.valid_quote(wrong)
    score = citation_metrics(["q1", "q2"], {"q1": [hit, {**hit, "end": 99999}]}, current)
    assert score["quote_span_precision"] == score["valid_quote_query_coverage"] == .5
    assert score["semantic_citation_accuracy"] is None


def test_missing_queries_and_duplicate_ranks_do_not_shrink_denominator():
    result = retrieval_metrics({"a": ["D2"], "b": ["D1"]}, {"a": ["D1", "D1", "D2"]}, {"D1", "D2"}, k=3)
    assert result["count"] == 2 and result["missing_query_results"] == 1
    assert result["recall_at_k"] == .5 and result["mrr_at_k"] == pytest.approx(1 / 6)
    result = retrieval_metrics({"a": ["D1"]}, {"a": ["unknown", "D1"]}, {"D1"}, k=1)
    assert result["recall_at_k"] == result["mrr_at_k"] == 0
    assert result["unknown_ranked_document_ids"] == 1
    with pytest.raises(ValueError):
        retrieval_metrics({"a": ["D1"]}, {"other": []}, {"D1"})
    malformed = retrieval_metrics({"a": ["D1"]}, {"a": [{}, "D1"]}, {"D1"}, k=2)
    assert malformed["mrr_at_k"] == .5 and malformed["unknown_ranked_document_ids"] == 1


def test_loader_observes_revocation_without_cached_approval(tmp_path):
    doc, review = example()
    path, ledger = tmp_path / "corpus.jsonl", tmp_path / "reviews.jsonl"
    path.write_text(json.dumps(doc) + "\n")
    path.chmod(0o600)
    append_record(ledger, review)
    assert load_corpus(path, ledger).search("연구실")
    append_record(ledger, {**review, "action": "revoke"})
    with pytest.raises(PermissionError):
        load_corpus(path, ledger)
    path.chmod(0o644)
    with pytest.raises(PermissionError):
        load_corpus(path, ledger)


def test_page_span_drift_duplicate_documents_and_query_bounds_are_refused():
    doc, review = example()
    bad = copy.deepcopy(doc)
    bad["spans"][0]["start"] = 1
    with pytest.raises(ValueError, match="SPAN"):
        ReferenceCorpus([bad], {subject_hash(bad): {**review, "subject_sha256": subject_hash(bad)}})
    with pytest.raises(ValueError):
        ReferenceCorpus([doc, doc], {subject_hash(doc): review})
    with pytest.raises(ValueError):
        corpus().search("x", limit=True)


def test_mcp_checks_case_capability_before_reference_loading(monkeypatch):
    from recase import mcp_server
    def denied(*_):
        raise PermissionError("scope denied")
    monkeypatch.setattr(mcp_server, "scoped", denied)
    monkeypatch.setenv("RECASE_REFERENCE_CORPUS", "/never-read")
    monkeypatch.setenv("RECASE_REFERENCE_REVIEWS", "/never-read")
    with pytest.raises(PermissionError, match="scope denied"):
        mcp_server.search_reference_judgments("case", 1, "bad", "query")


def test_actual_stdio_mcp_observes_approved_fixture_and_later_revocation(tmp_path, monkeypatch):
    import asyncio
    from recase.mcp_client import connect
    from recase.store import Store
    doc, review = example()
    path, ledger = tmp_path / "corpus.jsonl", tmp_path / "reviews.jsonl"
    path.write_text(json.dumps(doc) + "\n")
    path.chmod(0o600)
    append_record(ledger, review)
    monkeypatch.setenv("RECASE_REFERENCE_CORPUS", str(path))
    monkeypatch.setenv("RECASE_REFERENCE_REVIEWS", str(ledger))
    store = Store(tmp_path / "fixture.db")
    demo = store.new_demo()
    case = store.cases(demo["user_id"])[0]
    async def check():
        async with connect(store.path, "synthetic-ephemeral-mcp-secret") as client:
            result = await client.call("search_reference_judgments", demo["user_id"], case["id"], 1, query="연구실")
            assert result["status"] == "AVAILABLE_APPROVED_CONTEXT_ONLY"
            assert result["hits"][0]["document_id"] == doc["doc_id"]
            assert result["hits"][0]["document_type"] == "reference_judgment"
            assert result["hits"][0]["source_type"] == "synthetic_fixture"
            append_record(ledger, {**review, "action": "revoke"})
            blocked = await client.call("search_reference_judgments", demo["user_id"], case["id"], 1, query="연구실")
            assert blocked["status"] == "BLOCKED" and blocked["hits"] == []
    asyncio.run(check())
