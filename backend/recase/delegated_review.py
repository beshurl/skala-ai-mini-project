"""Explicit, packet-bound public KLUE delegation; never a human attestation.

These operator-owned records provide local audit integrity, not proof of identity
against a privileged operator. They do not authorize judgments or blind finals.
"""
import json
import os
from pathlib import Path

from recase.ledger import digest, file_digest, read_ledger

GRANT = "delegated_nli_grant.json"
REVIEWS = "reviews/delegated_ai_reviews.jsonl"
COVERAGE = "delegated_known_history.json"
DATASETS = {"nli_train_candidates": "training", "nli_validation": "evaluation"}
STATEMENT = "공개 NLI만 AI 위임 검토 허용"


def private_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077:
        raise PermissionError("Delegation records must be regular operator-owned mode0600 files")
    return path


def load_delegation(packet, items):
    """Return no alternate permission for legacy packets without an explicit seal."""
    packet = Path(packet)
    manifest = json.loads((packet / "tool_manifest.json").read_text())
    if GRANT not in manifest:
        if (packet / GRANT).exists():
            raise PermissionError("Unsealed delegation refused")
        return None
    grant_path = private_file(packet / GRANT)
    grant = json.loads(grant_path.read_text())
    if (manifest[GRANT] != file_digest(grant_path)
            or grant.get("kind") != "public_klue_nli_user_delegation_v1"
            or grant.get("authorization_statement") != STATEMENT
            or grant.get("authorized_by") != "direct_user_message"
            or grant.get("protocol_sha256") != file_digest(packet / "protocol.json")
            or grant.get("scope") != "local_public_development_nli_only"
            or grant.get("human_reviewed") is not False
            or grant.get("blind_final_eligible") is not False
            or grant.get("maximum_training_attempts") != 3):
        raise PermissionError("Explicit bounded public NLI delegation required")
    subjects = grant.get("subjects", [])
    allowed = {s["subject_sha256"]: s for s in subjects}
    if (len(subjects) != 450 or len(allowed) != 450
            or len({s["sample_id"] for s in subjects}) != 450
            or sum(s["dataset"] == "nli_train_candidates" for s in subjects) != 300
            or sum(s["dataset"] == "nli_validation" for s in subjects) != 150):
        raise PermissionError("Delegation is limited to the specifically authorized300+150 subjects")
    for ref in grant.get("source_files", []):
        if file_digest(ref["path"]) != ref["sha256"]:
            raise PermissionError("Delegation-bound provenance changed")
    if not grant.get("source_files"):
        raise PermissionError("Source and authorization provenance required")
    latest = {}
    for envelope in read_ledger(private_file(packet / REVIEWS)):
        review = envelope["payload"]
        if (review.get("kind") != "delegated_nli_review" or review.get("grant_sha256") != file_digest(grant_path)
                or review.get("actor_kind") != "delegated_ai_review"
                or review.get("human_reviewed") is not False
                or review.get("human_attestation_created") is not False
                or review.get("subject_sha256") not in allowed):
            raise PermissionError("Invalid or out-of-scope delegated review")
        latest[review["subject_sha256"]] = review
    if set(latest) != set(allowed):
        raise PermissionError("All450 authorized subjects need explicit AI decisions, including quarantine")
    for item in items:
        inp = item["subject"]["input"]
        if inp["dataset"] in DATASETS:
            ref = allowed.get(item["subject_sha256"], {})
            if ref.get("sample_id") != item["sample_id"] or ref.get("dataset") != inp["dataset"]:
                raise PermissionError("Current packet contains a subject outside the user grant")
    return {"grant": grant, "reviews": latest, "allowed": allowed, "packet": packet}


def delegated_permitted(item, delegation):
    if not delegation:
        return False
    subject = item["subject"]
    inp = subject["input"]
    review = delegation["reviews"].get(item["subject_sha256"], {})
    requested = DATASETS.get(inp.get("dataset"))
    source = inp.get("source_ref", "")
    return bool(requested and inp.get("task") == "nli" and inp.get("source_id") == "klue_nli"
        and (source.startswith("raw/klue_nli/klue_benchmark/klue-nli-v1.1/") or source == "authored_rewrites.json")
        and subject.get("rights_basis") == "CC-BY-SA-4.0"
        and subject.get("requested_use") == requested and digest(subject) == item["subject_sha256"]
        and review.get("sample_id") == item["sample_id"] and review.get("decision") == "accept"
        and review.get("label") == subject["answer"]["target"].get("label")
        and isinstance(review.get("rationale"), str) and len(review["rationale"].strip()) >= 10
        and review.get("privacy_disposition") == "AI_LOCAL_PUBLIC_NLI_ONLY"
        and review.get("source_integrity") == "PASS"
        and review.get("permissions") == {"processing": True, requested: True}
        and review.get("license_hashes") == {name: file_digest(name) for name in subject.get("license_files", [])}
        and bool(subject.get("license_files")))


def review_kind(item, human, delegation):
    # A later explicit human rejection must never be bypassed by AI delegation.
    from recase.prepared_data import permitted
    if human and human.get("action") == "reject":
        return None
    if permitted(item, human):
        return "human_attestation"
    return "delegated_ai_review" if delegated_permitted(item, delegation) else None


def known_history_covered(delegation, entries):
    if not delegation:
        return False
    packet = delegation["packet"]
    manifest = json.loads((packet / "tool_manifest.json").read_text())
    path = private_file(packet / COVERAGE)
    coverage = json.loads(path.read_text())
    return bool(manifest.get(COVERAGE) == file_digest(path)
        and coverage.get("kind") == "delegated_known_local_history_snapshot"
        and coverage.get("actor_kind") == "delegated_ai_review"
        and coverage.get("exposures_sha256") == digest(entries)
        and coverage.get("grant_sha256") == file_digest(packet / GRANT)
        and coverage.get("external_and_pretraining_exposure") == "UNKNOWN"
        and coverage.get("blind_final_eligible") is False
        and coverage.get("human_attestation_created") is False)
