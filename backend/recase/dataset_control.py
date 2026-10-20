"""Fail-closed dataset intake, family/near-duplicate and exposure controls.

Signatures and reports contain no prompt/answer text. Similarity is a candidate
detector, not a claim that semantic duplicates have all been found.
"""
import re
import unicodedata
from collections import Counter
from pathlib import Path

from recase.ledger import digest, file_digest, read_ledger

FAMILIES = ("case_family", "document_family", "scenario_family", "template_family")
SPLITS = {"train", "validation", "final", "development", "candidate"}
PURPOSES = {"processing", "training", "rag", "display", "redistribution"}
NEAR_THRESHOLD = 0.82
AUDIT_VERSION = "family-exposure-v1"


def subject_hash(row):
    # Bind ALL source, permission, label, family and prompt fields, excluding only
    # derived approval annotations. A correction requires a new human attestation.
    return digest({k: v for k, v in row.items() if k not in ("review", "attestation")})


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def signature(row):
    prompt = row.get("prompt", row.get("text", ""))
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Non-empty prompt/text required")
    normalized = normalize(prompt)
    grams = {digest(normalized[i:i + 3]) for i in range(max(1, len(normalized) - 2))}
    return {"sample_id": row.get("sample_id", row.get("case_id", row.get("doc_id"))),
            "exact": digest(prompt), "normalized": digest(normalized),
            "number_masked": digest(re.sub(r"\d+", "#", normalized)),
            "grams": sorted(grams), "length": len(normalized),
            "families": {key: row.get(key) for key in FAMILIES}}


def related(a, b, threshold=NEAR_THRESHOLD):
    reasons = [key for key in FAMILIES if a["families"].get(key) and a["families"][key] == b["families"].get(key)]
    if a["exact"] == b["exact"]:
        reasons.append("exact")
    elif a["normalized"] == b["normalized"]:
        reasons.append("normalized_exact")
    elif a["number_masked"] == b["number_masked"]:
        reasons.append("numeric_template")
    else:
        left, right = set(a["grams"]), set(b["grams"])
        # Short snippets are too unstable for this heuristic; exact/family gates
        # above still apply. Human semantic review is mandatory for every source.
        if min(a["length"], b["length"]) >= 24 and len(left & right) / max(1, len(left | right)) >= threshold:
            reasons.append("near_trigram")
    return reasons


def latest_reviews(ledger_path):
    rows = read_ledger(ledger_path)
    latest = {}
    for entry in rows:
        event = entry["payload"]
        if event.get("action") in {"approve", "revoke"}:
            latest[event["subject_sha256"]] = event
    return latest


def permitted(row, use, review):
    permission = "processing" if use == "evaluation" else use
    return bool(
        permission in PURPOSES and review
        and review.get("action") == "approve"
        and review.get("actor_kind") == "human_attestation"
        and review.get("subject_sha256") == subject_hash(row)
        and review.get("reviewer") and review.get("reviewed_at")
        and review.get("privacy_checked") is True
        and row.get("rights_basis", "").strip()
        and row.get("permissions", {}).get("processing") is True
        and row.get("permissions", {}).get(permission) is True
        and review.get("permissions", {}).get("processing") is True
        and review.get("permissions", {}).get(permission) is True
        and (use not in {"training", "evaluation"} or review.get("labels_checked") is True)
        and (row.get("source_type") != "actual_judgment" or row.get("clean_sha256"))
    )


def audit(rows, exposures, reviews=None, history_complete=False):
    reviews = reviews or {}
    if not 1 <= len(rows) <= 2000 or len(exposures) > 10000:
        raise ValueError("Audit bounds: 1..2000 candidates, at most 10000 history entries")
    signatures = [signature(row) for row in rows]
    ids = [s["sample_id"] for s in signatures]
    issues, conflicts, parents = [], [], list(range(len(rows)))

    def issue(code, sample=None):
        issues.append({"code": code, **({"sample_id": sample} if sample else {})})

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    if not history_complete:
        issue("EXPOSURE_HISTORY_NOT_ATTESTED_COMPLETE")
    for i, row in enumerate(rows):
        sid, split = ids[i], row.get("split")
        if not isinstance(sid, str) or not sid.strip() or ids.count(sid) > 1:
            issue("MISSING_OR_DUPLICATE_ID", sid)
        if split not in SPLITS:
            issue("INVALID_SPLIT", sid)
        if "prompt" in row:
            from evaluation.scoring import allowed_evidence, parse_response
            parsed, error = parse_response(row.get("answer", ""), allowed_evidence(row))
            if error or parsed["label"] != row.get("label"):
                issue("INVALID_TARGET_CONTRACT_OR_LABEL", sid)
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in FAMILIES):
            issue("MISSING_FAMILY_METADATA", sid)
        use = "training" if split == "train" else "evaluation"
        if not permitted(row, use, reviews.get(subject_hash(row))):
            issue("HUMAN_REVIEW_OR_PURPOSE_APPROVAL_REQUIRED", sid)
        if split in {"candidate", "development"}:
            issue("DEVELOPMENT_ONLY", sid)
        for j in range(i):
            reasons = related(signatures[i], signatures[j])
            if reasons:
                parents[find(i)] = find(j)
                cross = split != rows[j].get("split")
                exact = bool({"exact", "normalized_exact"} & set(reasons))
                if cross or exact or "near_trigram" in reasons or "numeric_template" in reasons:
                    conflicts.append({"left": ids[j], "right": sid, "reasons": reasons, "scope": "current", "cross_split": cross})
                    issue("CROSS_SPLIT_FAMILY_OR_DUPLICATE" if cross else "WITHIN_SPLIT_DUPLICATE_REVIEW_REQUIRED", sid)
        if split in {"validation", "final"}:
            for old in exposures:
                reasons = related(signatures[i], old["signature"])
                if reasons and (split == "final" or old["purpose"] == "training"):
                    conflicts.append({"left": old["signature"]["sample_id"], "right": sid,
                                      "reasons": reasons, "scope": "history", "prior_purpose": old["purpose"]})
                    issue("PRIOR_EXPOSURE", sid)
    groups = {}
    for i, sid in enumerate(ids):
        groups.setdefault(str(find(i)), []).append(sid)
    return {"version": AUDIT_VERSION, "status": "PASS" if not issues else "BLOCKED",
            "candidate_count": len(rows), "history_count": len(exposures),
            "history_complete": history_complete, "near_threshold": NEAR_THRESHOLD,
            "issue_counts": dict(Counter(x["code"] for x in issues)), "issues": issues,
            "conflicts": conflicts, "connected_families": list(groups.values()),
            "split_counts": dict(Counter(row.get("split") for row in rows)),
            "limitations": ["Lexical similarity misses semantic paraphrases; human review required.",
                            "Hash chains detect edits, not a malicious same-UID operator rewriting all records."]}


def exposure_entries(path):
    return [e["payload"] for e in read_ledger(path) if e["payload"].get("kind") == "exposure"]


def file_identity(path):
    return {"path": str(Path(path).resolve()), "sha256": file_digest(path)}
