"""Local reference search with fresh per-purpose approvals and exact quote spans.

Reference judgments supply context, never facts proving the current case.
"""
import hashlib
import json
import os
import stat
from pathlib import Path

from recase.dataset_control import latest_reviews, subject_hash
from recase.governance import approved_for
from recase.search import terms


class ReferenceCorpus:
    def __init__(self, documents, reviews, chunk_size=800):
        if not 100 <= chunk_size <= 2000 or len(documents) > 1000:
            raise ValueError("REFERENCE_CORPUS_BOUNDS")
        self.documents, self.chunks = {}, []
        total = 0
        for document in documents:
            review = reviews.get(subject_hash(document))
            # Display is independently required because returned hits contain text.
            if not all(approved_for(document, use, review) for use in ("rag", "display")):
                continue
            text, doc_id = document.get("text"), document.get("doc_id")
            if (not isinstance(text, str) or not text.strip() or len(text) > 128000
                    or not isinstance(doc_id, str) or not doc_id or len(doc_id) > 128
                    or doc_id in self.documents
                    or document.get("source_type") not in {"actual_judgment", "synthetic_fixture"}):
                raise ValueError("INVALID_APPROVED_REFERENCE")
            if document.get("clean_sha256") != hashlib.sha256(text.encode()).hexdigest():
                raise ValueError("REFERENCE_TEXT_HASH_CHANGED")
            total += len(text.encode())
            if total > 20 * 1024 * 1024:
                raise ValueError("REFERENCE_CORPUS_BYTE_BUDGET")
            spans = document.get("spans") or [{"start": 0, "end": len(text), "text": text, "page": None}]
            previous = 0
            for span in spans:
                start, end = span.get("start"), span.get("end")
                page = span.get("page")
                if (type(start) is not int or type(end) is not int or not previous <= start < end <= len(text)
                        or span.get("text") != text[start:end]
                        or page is not None and (type(page) is not int or page < 1)):
                    raise ValueError("INVALID_REFERENCE_SOURCE_SPAN")
                previous = end
                for offset in range(start, end, chunk_size):
                    stop = min(offset + chunk_size, end)
                    self.chunks.append({"document_id": doc_id, "chunk_id": f"{doc_id}:{offset}:{stop}",
                        "start": offset, "end": stop, "page": page, "quote": text[offset:stop],
                        "source_type": document["source_type"],
                        "document_type": "reference_judgment", "role": "context_not_current_case_evidence",
                        "index_version": "approved-keyword-bigram-v1"})
            self.documents[doc_id] = document
        if not self.documents:
            raise PermissionError("NO_RIGHTS_APPROVED_REVIEWED_REFERENCE_CORPUS")

    def search(self, query, limit=5):
        if not isinstance(query, str) or len(query) > 1000 or type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("REFERENCE_QUERY_BOUNDS")
        wanted = terms(query)
        hits = [{**chunk, "score": len(wanted & terms(chunk["quote"]))} for chunk in self.chunks]
        hits = [h for h in hits if h["score"]]
        return sorted(hits, key=lambda h: (-h["score"], h["document_id"], h["start"]))[:limit]

    def valid_quote(self, citation):
        if not isinstance(citation, dict) or citation.get("document_type") != "reference_judgment":
            return False
        if not isinstance(citation.get("document_id"), str):
            return False
        document = self.documents.get(citation.get("document_id"))
        if document is None or citation.get("source_type") != document["source_type"]:
            return False
        start, end = citation.get("start"), citation.get("end")
        return bool(type(start) is int and type(end) is int and 0 <= start < end <= len(document["text"])
                    and citation.get("quote") == document["text"][start:end])


def load_corpus(path, review_ledger):
    path = Path(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 24 * 1024 * 1024):
        raise PermissionError("PRIVATE_REFERENCE_CORPUS_REQUIRED")
    documents = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    # Reload approvals for every search invocation; revocation/text changes take effect.
    return ReferenceCorpus(documents, latest_reviews(review_ledger))


def retrieval_metrics(qrels, rankings, allowed_documents, k=5):
    if not qrels or type(k) is not int or not 1 <= k <= 10 or set(rankings) - set(qrels):
        raise ValueError("FIXED_QUERY_IDS_AND_K_REQUIRED")
    allowed = set(allowed_documents)
    if any(not set(relevant) or not set(relevant) <= allowed for relevant in qrels.values()):
        raise ValueError("NONEMPTY_VALID_GOLD_DOCUMENT_IDS_REQUIRED")
    recalls, reciprocal_ranks, invalid = [], [], 0
    for query_id, relevant in qrels.items():
        ranked = rankings.get(query_id, [])
        if not isinstance(ranked, list):
            raise ValueError("RANKING_LIST_REQUIRED")
        top = ranked[:k]
        invalid += sum(not isinstance(doc_id, str) or doc_id not in allowed for doc_id in top)
        gold = set(relevant)
        recalls.append(len({doc_id for doc_id in top if isinstance(doc_id, str)} & gold) / len(gold))
        reciprocal_ranks.append(next((1 / rank for rank, doc_id in enumerate(top, 1) if isinstance(doc_id, str) and doc_id in gold), 0))
    return {"count": len(qrels), "k": k, "recall_at_k": sum(recalls) / len(qrels),
            "mrr_at_k": sum(reciprocal_ranks) / len(qrels), "missing_query_results": len(set(qrels) - set(rankings)),
            "unknown_ranked_document_ids": invalid, "denominator_includes_missing_queries": True}


def citation_metrics(query_ids, citations, corpus):
    ids = list(query_ids)
    if not ids or len(set(ids)) != len(ids) or set(citations) - set(ids):
        raise ValueError("FIXED_UNIQUE_QUERY_IDS_REQUIRED")
    attempted, valid, covered = 0, 0, 0
    for query in ids:
        values = citations.get(query, [])
        if not isinstance(values, list):
            raise ValueError("CITATION_LIST_REQUIRED")
        checks = [corpus.valid_quote(value) for value in values]
        attempted += len(checks)
        valid += sum(checks)
        covered += any(checks)
    return {"query_count": len(ids), "attempted_citations": attempted, "valid_exact_spans": valid,
            "quote_span_precision": valid / attempted if attempted else None,
            "valid_quote_query_coverage": covered / len(ids),
            "semantic_citation_accuracy": None, "semantic_support_review": "NOT_RUN",
            "scope": "Exact approved-source identity/offset/text integrity only; not semantic support or current-case proof"}
