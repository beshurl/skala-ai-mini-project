"""Read-only stdio MCP. No file-path, network, reveal, or answer-store tools."""
import os
from mcp.server.fastmcp import FastMCP
from recase.capability import verify
from recase.search import search_evidence
from recase.store import Store, NotFound

server = FastMCP("recase-evidence", log_level="ERROR")


def scoped(case_id, evidence_version, access_token):
    owner = verify(os.environ["RECASE_MCP_SECRET"], access_token, case_id, evidence_version)
    return Store(os.environ["RECASE_DB"], read_only=True).snapshot(owner, case_id, evidence_version)


@server.tool()
def get_public_case(case_id: str, evidence_version: int, access_token: str) -> dict:
    """Read the authorized current case and released evidence only."""
    return scoped(case_id, evidence_version, access_token)


@server.tool()
def read_evidence(case_id: str, evidence_version: int, access_token: str, evidence_id: str) -> dict:
    """Read a released evidence record within the capability scope."""
    snapshot = scoped(case_id, evidence_version, access_token)
    for e in snapshot["evidence"]:
        if e["id"] == evidence_id:
            return {**e, "case_id": case_id, "evidence_version": evidence_version, "start": 0, "end": len(e["text"])}
    raise NotFound("EVIDENCE_NOT_FOUND")


@server.tool()
def search_case_evidence(case_id: str, evidence_version: int, access_token: str, query: str, limit: int = 5) -> dict:
    """Keyword baseline over released evidence of one authorized case."""
    return {"hits": search_evidence(scoped(case_id, evidence_version, access_token), query, limit)}


@server.tool()
def search_reference_judgments(case_id: str, evidence_version: int, access_token: str, query: str) -> dict:
    """Read freshly approved references as context, never current-case evidence."""
    scoped(case_id, evidence_version, access_token)
    corpus_path = os.environ.get("RECASE_REFERENCE_CORPUS")
    review_path = os.environ.get("RECASE_REFERENCE_REVIEWS")
    if not corpus_path or not review_path:
        return {"status": "BLOCKED", "reason": "NO_RIGHTS_APPROVED_REVIEWED_CORPUS", "hits": [], "document_type": "reference_judgment"}
    from recase.reference_search import load_corpus
    try:
        corpus = load_corpus(corpus_path, review_path)
    except (OSError, ValueError, PermissionError, KeyError, TypeError):
        return {"status": "BLOCKED", "reason": "REFERENCE_APPROVAL_OR_INTEGRITY_GATE_FAILED", "hits": [], "document_type": "reference_judgment"}
    return {"status": "AVAILABLE_APPROVED_CONTEXT_ONLY", "hits": corpus.search(query),
            "document_type": "reference_judgment", "role": "context_not_current_case_evidence"}


if __name__ == "__main__":
    if not os.environ.get("RECASE_MCP_SECRET") or not os.environ.get("RECASE_DB"):
        raise SystemExit("RECASE_DB and service-provided capability secret required")
    server.run(transport="stdio")
