"""Local automated checks of prepared public data; never a human attestation."""
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LABELS = {"entailment", "contradiction", "neutral"}
PATTERNS = {
    "phone": re.compile(r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "resident_id": re.compile(r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def flags_for_item(item, native=None):
    subject = item["subject"]
    flags = []
    if digest(subject) != item["subject_sha256"]:
        flags.append("SUBJECT_HASH_CHANGED")
    text = subject["input"]["prompt"] + "\n" + json.dumps(subject["answer"]["target"], ensure_ascii=False)
    flags.extend("PRIVACY_PATTERN_" + name.upper() for name, pattern in PATTERNS.items() if pattern.search(text))
    task = subject["input"]["task"]
    target = subject["answer"]["target"]
    if task == "nli":
        if target.get("label") not in LABELS:
            flags.append("UNKNOWN_NATIVE_LABEL")
        if native is not None:
            if native["gold_label"] != target["label"]:
                flags.append("PUBLISHER_TARGET_MISMATCH")
            votes = Counter(native.get(key) for key in ("label2", "label3", "label4", "label5") if native.get(key) in LABELS)
            if votes:
                majority, count = votes.most_common(1)[0]
                if count >= 3 and majority != target["label"]:
                    flags.append("UPSTREAM_AUXILIARY_MAJORITY_DISAGREES")
                elif len(votes) > 1:
                    flags.append("UPSTREAM_ANNOTATORS_DISAGREE")
            if native["premise"].strip() == native["hypothesis"].strip() and target["label"] != "entailment":
                flags.append("IDENTICAL_PROPOSITIONS_WITH_NON_ENTAILMENT")
    elif task == "legalqa":
        if not target.get("contexts"):
            flags.append("NO_PUBLISHER_SUPPORT_CONTEXT")
        if "contexts" in subject["input"] or "target" in subject["input"]:
            flags.append("GOLD_ANNOTATION_IN_MODEL_INPUT")
    elif task == "scenario":
        if not set(target["evidence_ids"]).issubset(subject["input"]["public_evidence_ids"]):
            flags.append("UNRELEASED_TARGET_CITATION")
        if subject["input"].get("scenario_family") == "clock-calibration":
            flags.append("CLAIM_MEANING_POSSIBILITY_VS_CONFIRMED_TIME_NEEDS_REVIEW")
    return flags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--source-collection", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    args.out.mkdir(parents=True, mode=0o700, exist_ok=False)
    cache, counts, rows = {}, Counter(), []
    with (args.prepared / "reviews/items.jsonl").open() as stream:
        items = [json.loads(line) for line in stream if line.strip()]
    for item in items:
        inp = item["subject"]["input"]
        native = None
        if inp["task"] == "nli":
            path = args.source_collection / inp["source_ref"]
            if path not in cache:
                cache[path] = json.loads(path.read_text())
            native = cache[path][inp["source_record_1based"]-1]
        flags = flags_for_item(item, native)
        counts.update(flags)
        rows.append({"sample_id": item["sample_id"], "subject_sha256": item["subject_sha256"],
                     "actor_kind": "automated_local_check", "automatic_checks_completed": True,
                     "human_reviewed": False, "flags": flags,
                     "disposition": "PRIORITY_HUMAN_REVIEW" if flags else "HUMAN_REVIEW_STILL_REQUIRED"})
    with (args.out / "automated_checks.jsonl").open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {"completed_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(), "records_checked": len(rows),
               "flagged_records": sum(bool(row["flags"]) for row in rows), "flag_counts": dict(counts),
               "local_human_reviews_created": 0, "purpose_approvals_created": 0, "model_calls": 0,
               "limitations": ["Auxiliary annotator agreement is not proof of semantic correctness.",
                               "Pattern checks miss names, addresses and indirect identifiers.",
                               "No external model or document transmission was used."]}
    with (args.out / "summary.json").open("x") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
