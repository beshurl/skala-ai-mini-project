#!/usr/bin/env python3
"""Read-only corpus integrity checks. No model evaluation, service import or training."""
import argparse
import hashlib
import json
from pathlib import Path

from recase.ledger import utc_now
from recase.public_collection import verify_receipts, write_json


def audit(collection, version):
    collection, version = Path(collection).absolute(), Path(version).absolute()
    if collection != version and collection not in version.parents:
        raise ValueError("Version outside collection")
    receipts = verify_receipts(collection)
    records = [json.loads(line) for line in (version / "quarantine/normalized-records.jsonl").read_text().splitlines()]
    references = [json.loads(line) for line in (version / "evaluation/reference-proposals.jsonl").read_text().splitlines()]
    inputs = [json.loads(line) for line in (version / "evaluation/document-inputs.jsonl").read_text().splitlines()]
    timeline = [json.loads(line) for line in (version / "processed/timeline-input-candidates.jsonl").read_text().splitlines()]
    summaries = json.loads((version / "audit.json").read_text())
    canonical = json.loads((collection / "closing-memos-canonical.json").read_text())
    checks = {
        "raw_receipts_chain_and_hashes":bool(receipts),
        "unique_record_ids":len({r["record_id"] for r in records})==len(records),
        "normalized_text_hashes":all(hashlib.sha256(r["text"].encode()).hexdigest()==r["text_sha256"] for r in records),
        "quarantined_no_service_or_training_approval":all(r["quarantine"] and r["human_reviewed"] is False
            and not r["training_eligible"] and not r["service_import_allowed"] for r in records),
        "reference_proposals_separate_from_document_inputs":{r["sample_id"] for r in references}=={r["sample_id"] for r in inputs}
            and all("proposed_reported_status" not in r and "outcome_label" not in r for r in inputs),
        "historical_candidates_ineligible":all(r["eligible"] is False and r["historical_snapshot_verified"] is False for r in timeline),
        "reported_fbi_total_matches_unique_uids":summaries["fbi_unique_notices"]==summaries["fbi_reported_total"]
            and summaries["fbi_page_totals_consistent"],
        "doj_title_sorted_catalog_complete":canonical["coverage_complete"] and len(canonical["sources"])==canonical["reported_total"],
        "private_file_and_directory_modes":all(not p.is_symlink() and not p.stat().st_mode & 0o077
            for p in [collection, *collection.rglob("*")]),
    }
    return {"checked_at":utc_now(), "kind":"DATA_INTEGRITY_ONLY", "checks":checks,
            "pass":all(checks.values()), "normalized_records":len(records),
            "model_evaluation":"NOT_RUN", "actual_case_accuracy":"NOT_MEASURED",
            "does_not_certify":["semantic label correctness", "complete anonymization", "case family independence",
                                "source freshness or historical authenticity", "copyright or purpose clearance", "OS account isolation"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--version", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.collection, args.version)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 2)
