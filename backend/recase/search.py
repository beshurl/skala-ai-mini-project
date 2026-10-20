"""A deterministic keyword baseline over an already-authorized evidence snapshot."""
import re
import unicodedata


def terms(text):
    text = unicodedata.normalize("NFC", text).lower()
    words = re.findall(r"[a-z0-9가-힣]+", text)
    return set(words) | {w[i:i+2] for w in words for i in range(len(w)-1)}


def search_evidence(snapshot, query, limit=5):
    if len(query) > 1000 or not 1 <= limit <= 10:
        raise ValueError("SEARCH_LIMIT")
    wanted = terms(query)
    hits = []
    for e in snapshot["evidence"]:
        common = wanted & terms(e["text"] + " " + e["title"])
        if common:
            hits.append({"evidence_id": e["id"], "case_id": snapshot["case_id"],
                         "evidence_version": snapshot["evidence_version"], "document_type": "case_evidence",
                         "source": "synthetic_fixture", "text": e["text"], "start": 0, "end": len(e["text"]),
                         "score": len(common), "index_version": "keyword-bigram-v1"})
    return sorted(hits, key=lambda h: (-h["score"], h["evidence_id"]))[:limit]
