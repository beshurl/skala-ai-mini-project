"""Quarantined public-case normalization and leakage audits, without model access."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from recase.ledger import append_record, digest, utc_now
from recase.public_collection import TextDocument, clean_text, decode_text, mask_contacts, verify_receipts, write_json, write_new

LABELS = ["UNRESOLVED_REPORTED", "IDENTITY_RESOLVED", "SUSPECT_IDENTIFIED",
          "ARREST_REPORTED", "CHARGES_REPORTED", "CONVICTION_REPORTED",
          "CLOSED_REPORTED", "UNKNOWN"]
# Source-reported states are proposals, not human-approved ground truth or guilt findings.
STORIES = {
    "golden_pre_updated": ("golden-state", "ARREST_REPORTED", "BACKFILLED_PRE_OUTCOME_PAGE"),
    "golden_sentence": ("golden-state", "CONVICTION_REPORTED", "OUTCOME_ONLY"),
    "dunes_identified": ("lady-of-dunes", "IDENTITY_RESOLVED", "IDENTITY_ONLY_NOT_HOMICIDE_CLOSURE"),
    "ricks_retrospective": ("james-ricks", "CONVICTION_REPORTED", "RETROSPECTIVE_ONLY"),
    "houston_retrospective": ("houston-1969", "CONVICTION_REPORTED", "RETROSPECTIVE_ONLY"),
    "thirty_year_retrospective": ("bonnet-1978", "CONVICTION_REPORTED", "RETROSPECTIVE_DATE_REVIEW"),
    "tinsley_pre": ("april-tinsley", "UNRESOLVED_REPORTED", "PRE_OUTCOME_SNAPSHOT_UNVERIFIED"),
    "seale_charged": ("seale-1964", "CHARGES_REPORTED", "PRE_VERDICT_SNAPSHOT_UNVERIFIED"),
    "seale_indictment": ("seale-1964", "CHARGES_REPORTED", "PRE_VERDICT_SNAPSHOT_UNVERIFIED"),
    "seale_verdict": ("seale-1964", "CONVICTION_REPORTED", "OUTCOME_ONLY"),
}


def jsonl(path, rows):
    return write_new(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def paragraph_text(doc):
    """Strip navigation and related-story cards; retain source paragraphs verbatim."""
    main = next((n for n in doc.nodes() if n.tag == "main"), None)
    main = main or next((n for n in doc.nodes() if n.attrs.get("id") == "main-content" and n.tag != "a"), doc.root)
    paragraphs = []
    def visit(node):
        classes = node.attrs.get("class", "").lower()
        if node.tag in {"nav", "footer", "header", "script", "style"} or any(
                word in classes for word in ("related-stor", "share-button", "sharing-tile", "related-content")):
            return
        if node.tag == "p":
            text = clean_text(node.text())
            if len(text) >= 35 and text not in paragraphs:
                paragraphs.append(text)
            return
        for child in node.children:
            if not isinstance(child, str):
                visit(child)
    visit(main)
    return paragraphs


def base_record(record_id, family_id, source, receipt, text):
    normalized = clean_text(text)
    hangul = len(re.findall(r"[가-힣]", normalized))
    latin = len(re.findall(r"[A-Za-z]", normalized))
    return {"schema": 1, "record_id": record_id, "family_id": family_id,
            "source": source, "source_receipt": receipt,
            "language_heuristic": "ko" if hangul > latin else "en" if latin else "und",
            "text": normalized, "text_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
            "contact_masked_text": mask_contacts(normalized),
            "privacy_status": "PARTIAL_AUTOMATED_MASKING_HUMAN_REVIEW_PENDING",
            "human_reviewed": False, "label_status": "UNREVIEWED",
            "purpose_approvals": {p: "PENDING" for p in ("processing", "training", "rag", "display", "redistribution")},
            "quarantine": True, "service_import_allowed": False,
            "training_eligible": False, "evaluation_eligible": False,
            "external_pretraining_exposure": "UNKNOWN"}


def fbi_record(item, receipt):
    uid = item.get("uid")
    if not isinstance(uid, str) or not uid:
        raise ValueError("FBI notice has no stable UID")
    # Do not replicate birth dates, physical descriptions, pictures or aliases into normalized input.
    text = "\n".join(clean_text(TextDocument(str(item.get(k) or "")).root.text())
                     for k in ("title", "description", "details", "remarks", "caution"))
    record = base_record("fbi:" + uid, "fbi:" + uid, "FBI_PUBLIC_WANTED_NOTICE", receipt, text)
    record.update({"source_url": item.get("url"), "publication": item.get("publication"),
                   "modified": item.get("modified"), "source_status": item.get("status"),
                   "poster_classification": item.get("poster_classification"), "subjects": item.get("subjects"),
                   "cold_case_keyword_candidate": bool(re.search(r"\bcold.case\b|\bunsolved\b", text, re.I)),
                   "cold_case_verified": False, "outcome_label": None})
    return record


def duplicate_audit(records, threshold=0.82):
    """Conservative text overlap candidates; does not certify event-family identity."""
    exact, shingles, inverted, near = defaultdict(list), [], defaultdict(list), []
    for i, record in enumerate(records):
        text = record["text"]
        if len(text) >= 80:
            exact[record["text_sha256"]].append(i)
        tokens = re.findall(r"\w+", text.lower())[:5000]
        grams = {tuple(tokens[j:j+5]) for j in range(len(tokens)-4)} if len(tokens) >= 20 else set()
        shingles.append(grams)
        for gram in grams:
            inverted[gram].append(i)
    candidates = set()
    for indexes in inverted.values():
        if len(indexes) > 80:  # Boilerplate-heavy bucket is reported separately below.
            continue
        for position, i in enumerate(indexes):
            for j in indexes[position+1:]:
                candidates.add((i, j))
    for i, j in sorted(candidates):
        if records[i]["text_sha256"] == records[j]["text_sha256"]:
            continue
        a, b = shingles[i], shingles[j]
        score = len(a & b) / len(a | b) if a | b else 0
        if score >= threshold:
            near.append({"left": records[i]["record_id"], "right": records[j]["record_id"],
                         "jaccard_5gram": round(score, 6)})
    return {"method": "full normalized exact text >=80 chars; first5000 word 5-gram Jaccard >=0.82",
            "threshold_frozen": threshold,
            "exact_groups": [[records[i]["record_id"] for i in ids] for ids in exact.values() if len(ids)>1],
            "near_pairs": near,
            "boilerplate_buckets_skipped": sum(len(ids)>80 for ids in inverted.values()),
            "limitation": "No semantic cross-language/person-family deduplication; human family review required; no eligible splits exported"}


def timeline_input(source_id, paragraphs):
    """Build an isolated candidate. Future-outcome documents have no input export."""
    if source_id == "seale_indictment":
        return {"record_id": "timeline:seale-indictment", "family_id": "seale-1964",
                "input_text": "\n".join(paragraphs), "as_of": "2007-01-25",
                "historical_snapshot_verified": False, "eligible": False,
                "review_flags": ["ARCHIVE_CONTENT_AND_DATE_REQUIRE_HUMAN_VERIFICATION"]}
    if source_id == "golden_pre_updated":
        kept = [p for p in paragraphs if not re.search(r"updated\s+april\s+25,?\s+2018", p, re.I)]
        return {"record_id": "timeline:golden-filtered", "family_id": "golden-state",
                "input_text": "\n".join(kept), "as_of": "2016-06-15",
                "historical_snapshot_verified": False, "eligible": False,
                "removed_paragraphs": len(paragraphs)-len(kept),
                "review_flags": ["BACKFILLED_PAGE", "AUTOMATIC_REMOVAL_IS_NOT_HISTORICAL_PROOF"]}
    return None


def eligibility_preflight(records):
    # This collector has no authority to approve a new corpus. Never accept JSON booleans
    # or review-queue edits in place of the existing signed/ledger-bound training gates.
    return {"checked_at": utc_now(), "records": len(records), "eligible_records": 0,
            "decision": "BLOCKED", "training": "NOT_RUN", "model_evaluation": "NOT_RUN",
            "actual_case_accuracy": "NOT_MEASURED",
            "blockers": ["PURPOSE_AND_PRIVACY_HUMAN_REVIEW_PENDING", "LABEL_AND_CASE_FAMILY_REVIEW_PENDING",
                         "INDEPENDENT_HISTORICAL_INPUTS_NOT_VERIFIED", "CURRENT_ANSWER_PATH_UID_PROBE_NOT_RUN",
                         "TRAINING_CYCLE_NOT_FROZEN", "SHARED_MODEL_LOCK_NOT_ACQUIRED"],
            "note": "Data integrity audits cannot substitute for model or operational validation"}


def prepare(root, output=None):
    root = Path(root)
    output = Path(output) if output else root
    if output != root and (root not in output.absolute().parents or output.is_symlink()):
        raise ValueError("Derived versions must remain inside the external collection")
    if (output / "audit.json").exists():
        raise FileExistsError("Use a new collection/version; never overwrite processed results")
    receipts = verify_receipts(root)
    manifests = [json.loads((root/"collection.json").read_text())]
    manifests += [json.loads(p.read_text()) for p in sorted(root.glob("supplement-*.json"))]
    closing_manifest = root / "closing-memos-canonical.json"
    if not closing_manifest.exists():
        closing_manifest = root / "closing-memos-complete.json"
    if not closing_manifest.exists():
        closing_manifest = root / "closing-memos.json"
    if closing_manifest.exists():
        manifests.append(json.loads(closing_manifest.read_text()))
    sources = [s for m in manifests for s in m.get("sources", [])]
    records, rejected, fbi_uids, snapshots, references, input_candidates, catalogs = [], [], set(), [], [], [], []
    pages = manifests[0]["fbi_pages"]
    for page in pages:
        obj = json.loads((root / page["receipt"]["path"]).read_bytes())
        for offset, item in enumerate(obj["items"]):
            try:
                record = fbi_record(item, page["receipt"])
                if record["record_id"] in fbi_uids:
                    rejected.append({"reason":"DUPLICATE_UID", "record_id":record["record_id"]})
                    continue
                fbi_uids.add(record["record_id"])
                records.append(record)
            except (ValueError, TypeError) as exc:
                rejected.append({"page":page["page"], "offset":offset, "reason":type(exc).__name__})
    for source in sources:
        decoded, encoding = decode_text((root / source["receipt"]["path"]).read_bytes(), source["receipt"].get("content_type", ""))
        doc = TextDocument(decoded)
        if source["kind"] in {"case_source", "closure_memo"}:
            paragraphs = paragraph_text(doc)
            non_paragraph_fallback = False
            if not paragraphs and source["kind"] == "closure_memo":
                main = next((n for n in doc.nodes("main")), None)
                if main and len(clean_text(main.text())) >= 35:
                    paragraphs = [clean_text(main.text())]
                    non_paragraph_fallback = True
            if not paragraphs:
                rejected.append({"source":source["id"], "reason":"NO_ARTICLE_PARAGRAPHS"})
                continue
            family, label, flag = STORIES.get(source["id"], (source["id"], "UNKNOWN", "CLOSING_MEMO_DISPOSITION_REVIEW_PENDING"))
            record = base_record(source["id"], family, "DOJ_CLOSING_CASE_PAGE" if source["kind"]=="closure_memo" else "OFFICIAL_CASE_NARRATIVE",
                                 source["receipt"], "\n".join(paragraphs))
            record.update({"source_url":source["url"], "metadata":doc.metadata(), "review_flags":[flag],
                           "proposed_reported_status":label, "label_origin":"AI_PROPOSED_NOT_HUMAN",
                           "historical_snapshot_verified":False, "decoded_encoding":encoding})
            if non_paragraph_fallback:
                record["review_flags"].append("NON_PARAGRAPH_HTML_METADATA_LAYOUT_REVIEW")
            records.append(record)
            if source["kind"] == "case_source":
                references.append(record)
                candidate = timeline_input(source["id"], paragraphs)
                if candidate:
                    candidate["source_receipt"] = source["receipt"]
                    input_candidates.append(candidate)
        elif source["kind"] == "public_missing_list":
            cards = [n for n in doc.nodes("li") if n.attrs.get("class") == "col-sm-4"]
            for card in cards:
                links = [n for n in card.descendants() if n.tag == "a"]
                match = next((re.search(r"fn_getLcmMssGet\('([0-9]+)'\)", n.attrs.get("onclick", "")) for n in links), None)
                if not match:
                    continue
                key = "safe182:" + match.group(1)
                record = base_record(key, key, "SAFETYDREAM_VISIBLE_MISSING_NOTICE", source["receipt"], clean_text(card.text()))
                record.update({"outcome_label":None, "cold_case_verified":False,
                               "source_url":source["url"], "coverage":"VISIBLE_LIST_SNAPSHOT_ONLY_TOTAL_INCONSISTENT"})
                records.append(record)
            reported_match = re.search(r"전체\s*건수\s*:\s*([\d,]+)\s*건", clean_text(doc.root.text()))
            reported = int(reported_match.group(1).replace(",", "")) if reported_match else None
            snapshots.append({"source":"SafetyDream", "visible_cards":len(cards), "reported_count":reported,
                              "coverage":"VISIBLE_LIST_SNAPSHOT_ONLY_TOTAL_UNVERIFIED", "api_status":"AUTH_REQUIRED"})
        elif source["kind"] == "catalog_only":
            title = next((clean_text(n.text()) for n in doc.nodes("title")), "")
            tables = [clean_text(n.text()) for n in doc.nodes("table") if "상세정보" in n.text()]
            catalogs.append({"source_id":source["id"], "title":title, "source_url":source["url"],
                             "metadata":tables, "raw_record_body":"NOT_ACQUIRED", "source_receipt":source["receipt"]})
    pdfs = json.loads((root / "closing-documents.json").read_text()) if (root / "closing-documents.json").exists() else {"documents":[], "failures":[]}
    if (root / "closing-documents-supplement.json").exists():
        supplement = json.loads((root / "closing-documents-supplement.json").read_text())
        pdfs["documents"] += supplement["documents"]
        pdfs["failures"] = [f for f in pdfs["failures"] if f["url"] not in supplement.get("resolved_prior_failure_urls",[])] + supplement["failures"]
    sparse_pdf_pages = 0
    reason_patterns = {"INSUFFICIENT_EVIDENCE_MENTION":r"insufficient evidence|lack of evidence|lack of sufficient evidence",
                       "DECEASED_SUBJECT_MENTION":r"subject.{0,90}(?:deceased|died)|(?:deceased|dead).{0,50}subject",
                       "LIMITATIONS_MENTION":r"statute of limitations|limitations period",
                       "JURISDICTION_MENTION":r"lack.{0,30}jurisdiction|no federal jurisdiction",
                       "UNIDENTIFIED_SUBJECT_MENTION":r"unknown subject|unidentified subject"}
    for pdf in pdfs["documents"]:
        raw = (root / pdf["extraction_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pdf["extraction_sha256"]:
            raise ValueError("PDF extraction hash mismatch")
        extracted = json.loads(raw)
        sparse = [p["page"] for p in extracted["pages"] if len(p["text"].strip()) < 40]
        sparse_pdf_pages += len(sparse)
        text = "\n".join(page["text"] for page in extracted["pages"])
        record = base_record(pdf["id"], min(pdf["cases"]), "DOJ_CLOSING_REPORT_PDF", pdf["receipt"], text)
        mentions = {name:[page["page"] for page in extracted["pages"] if re.search(pattern, page["text"], re.I|re.S)]
                    for name,pattern in reason_patterns.items()}
        record.update({"source_url":pdf["url"], "linked_case_ids":pdf["cases"],
                       "pdf_pages":pdf["pages"], "extraction_status":pdf["extraction_status"],
                       "review_flags":["CLOSURE_IS_NOT_CASE_SOLUTION", "PAGE_TEXT_AND_REDACTIONS_REQUIRE_HUMAN_REVIEW"],
                       "reason_keyword_mentions":mentions, "reason_mentions_are_labels":False,
                       "sparse_text_pages_require_OCR_or_manual_review":sparse,
                       "outcome_label":None, "historical_snapshot_verified":False})
        records.append(record)
    # Define the evaluation contract before any model predictions; this command never loads a model.
    protocol = {"schema":1, "frozen_before_model_predictions":True, "created_at":utc_now(),
                "task":"Extract what an official document reports as of its verified date; evidence sufficiency review",
                "labels":LABELS, "target_excludes":["guilt_probability", "perpetrator_prediction", "case_solve_rate"],
                "metrics_planned":["all_items_accuracy", "macro_f1", "citation_span_validity", "abstention_rate"],
                "missing_or_invalid_predictions":"INCLUDED_IN_DENOMINATOR_AS_INCORRECT",
                "split_unit":"HUMAN_VERIFIED_CASE_FAMILY", "same_family_cross_split":"FORBIDDEN",
                "comparison":"Refuse differing dataset/model/prompt/retrieval/generation hashes; A-F NOT_RUN",
                "historical_inputs":"Human-confirmed pre-outcome snapshot only; no retrospective text trimming as proof",
                "final_test_eligibility":"NONE; source selection and reference proposals exposed in development",
                "required_gates":["purpose_rights", "human_privacy", "human_label", "family_and_exposure", "current_OS_UID_answer_hash_denial", "model_lock", "freeze_cycle_max3"]}
    write_json(output / "evaluation/protocol.json", protocol)
    audit = duplicate_audit(records)
    duplicate_ids = set()
    for group in audit["exact_groups"]:
        duplicate_ids.update(group[1:])
    near_ids = {pair[k] for pair in audit["near_pairs"] for k in ("left", "right")}
    for record in records:
        record["duplicate_disposition"] = ("EXACT_DUPLICATE_HOLD" if record["record_id"] in duplicate_ids
            else "NEAR_DUPLICATE_FAMILY_REVIEW" if record["record_id"] in near_ids else "NO_TEXT_MATCH_FOUND_FAMILY_REVIEW_PENDING")
    jsonl(output / "quarantine/normalized-records.jsonl", records)
    jsonl(output / "quarantine/reference-sources.jsonl", references)
    jsonl(output / "processed/timeline-input-candidates.jsonl", input_candidates)
    jsonl(output / "processed/catalog-metadata.jsonl", catalogs)
    jsonl(output / "processed/deduplicated-review-candidates.jsonl", [r for r in records if r["record_id"] not in duplicate_ids])
    jsonl(output / "evaluation/document-inputs.jsonl", [{"sample_id":r["record_id"], "family_id":r["family_id"],
          "task":"REPORT_STATUS_FROM_THIS_DOCUMENT_ONLY", "input_text":r["text"],
          "source_receipt":r["source_receipt"], "eligible":False} for r in references])
    jsonl(output / "evaluation/reference-proposals.jsonl", [{"sample_id":r["record_id"],
          "proposed_reported_status":r["proposed_reported_status"], "human_reviewed":False,
          "case_solution_or_guilt_target":False} for r in references])
    jsonl(output / "review/queue.jsonl", [{"record_id":r["record_id"], "source_sha256":r["source_receipt"]["sha256"],
         "text_sha256":r["text_sha256"], "family_id":r["family_id"], "reviewer":None, "reviewed_at":None,
         "processing":None, "training":None, "rag":None, "display":None, "redistribution":None,
         "privacy":None, "label":None, "case_family":None, "notes":None} for r in records])
    write_json(output / "review/duplicates.json", audit)
    write_json(output / "review/rejected-records.json", rejected)
    preflight = eligibility_preflight(records)
    write_json(output / "evaluation/preflight.json", preflight)
    # Record automation separately from actual AI/human reading. Never call automated processing human review.
    append_record(output / "logs/exposure.jsonl", {"event":"AUTOMATED_NORMALIZATION_ALL_RECORDS", "record_count":len(records),
                  "record_manifest_sha256":digest([{k:r[k] for k in ("record_id","text_sha256")} for r in records]),
                  "ai_text_reading":"ONLY_SELECTED_SOURCE_ARTICLES_AND_POLICY_PAGES", "human_reviewed":False,
                  "external_pretraining_exposure":"UNKNOWN", "blind_final_test":False})
    counts = Counter(r["source"] for r in records)
    summary = {"schema":1, "prepared_at":utc_now(), "data_location":str(root), "records":len(records),
               "counts":dict(counts), "official_narrative_families":len({r["family_id"] for r in references}),
               "language_heuristic_counts":dict(Counter(r["language_heuristic"] for r in records)),
               "proposed_status_counts":dict(Counter(r["proposed_reported_status"] for r in references)),
               "fbi_pages":len(pages), "fbi_reported_total":manifests[0]["fbi_reported_total_start"],
               "fbi_unique_notices":len(fbi_uids), "fbi_page_totals_consistent":len({p["total"] for p in pages})==1,
               "fbi_cold_keyword_candidates":sum(r.get("cold_case_keyword_candidate",False) for r in records),
               "fbi_cold_cases_human_verified":0, "source_response_receipts":len(receipts),
               "list_snapshots":snapshots, "catalog_documents":len(catalogs),
               "rejected_records":len(rejected), "exact_duplicate_groups":len(audit["exact_groups"]),
               "near_duplicate_pairs":len(audit["near_pairs"]), "timeline_input_candidates":len(input_candidates),
               "exact_duplicate_copies_held":len(duplicate_ids), "deduplicated_review_candidates":len(records)-len(duplicate_ids),
               "doj_case_pages_reported_total":manifests[-1].get("reported_total"),
               "doj_case_pages_coverage_complete":manifests[-1].get("coverage_complete",False),
               "doj_report_documents":len(pdfs["documents"]), "doj_report_pages":sum(p["pages"] for p in pdfs["documents"]),
               "doj_pdf_failures":pdfs["failures"],
               "doj_pdf_ocr_required":sum(p["extraction_status"]=="OCR_REQUIRED" for p in pdfs["documents"]),
               "pdf_sparse_text_pages_require_OCR_or_manual_review":sparse_pdf_pages,
               "historical_inputs_verified":0, "human_approved_records":0, "eligible_training_records":0,
               "training":"NOT_RUN", "model_evaluation":"NOT_RUN", "actual_case_accuracy":"NOT_MEASURED",
               "acquisition_failures":[f for m in manifests for f in m.get("failures",[])],
               "restricted_sources":{"NamUs":"AUTH_REQUIRED_NO_EXPORT", "SafetyDream_API":"MOBILE_IDENTITY_AUTH_REQUIRED",
                  "Law_API":"OC_APPLICATION_AUTH_REQUIRED", "NationalArchives_raw_files":"NOT_ACQUIRED_CATALOG_ONLY"},
               "protection":"PRIVATE_LOCAL_FOLDER_NOT_A_SEPARATE_ENCRYPTED_VOLUME", "service_imports":0}
    write_json(output / "audit.json", summary)
    return summary
