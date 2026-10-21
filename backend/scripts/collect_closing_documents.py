#!/usr/bin/env python3
"""Acquire explicitly linked DOJ closing reports; extract local PDF pages without a model."""
import argparse
import hashlib
import io
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from pypdf import PdfReader

from recase.public_collection import PublicCollector, TextDocument, clean_text, verify_receipts, write_json


def collect_documents(root):
    root = Path(root).absolute()
    project = Path(__file__).resolve().parents[2]
    if root == project or project in root.parents:
        raise ValueError("Store data outside the code project")
    if (root / "closing-documents.json").exists():
        raise FileExistsError("Use a new collection; never replace report extraction")
    verify_receipts(root)
    manifest = json.loads((root / "closing-memos-canonical.json").read_text())
    links = {}
    for source in manifest["sources"]:
        doc = TextDocument((root / source["receipt"]["path"]).read_text(errors="replace"))
        main = next((n for n in doc.nodes("main")), doc.root)
        for node in main.descendants():
            if node.tag != "a":
                continue
            href = node.attrs.get("href", "")
            if not re.search(r"/crt/(?:media/|(?:page/)?file/)|/sites/default/files/.+\.pdf", href):
                continue
            url = urljoin(source["url"], href)
            link = links.setdefault(url, {"url":url, "cases":[], "anchor_labels":[]})
            link["cases"].append(source["id"])
            link["anchor_labels"].append(clean_text(node.text()))
    if not 1 <= len(links) <= 400:
        raise ValueError("Unexpected linked document count")
    collector, docs, failures = PublicCollector(root), [], []
    for i, link in enumerate(links.values()):
        try:
            data, receipt = collector.fetch(link["url"], allow_pdf=True)
            if not data.startswith(b"%PDF-"):
                raise ValueError("Linked report is not a PDF")
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 2000:
                raise ValueError("Encrypted or over-budget report")
            pages = [{"page":j+1, "text":page.extract_text() or ""} for j,page in enumerate(reader.pages)]
            if sum(len(p["text"]) for p in pages) > 2_000_000:
                raise ValueError("Extracted text exceeds per-document budget")
            doc_id = "doj-pdf:" + hashlib.sha256(link["url"].encode()).hexdigest()[:20]
            extraction = {"document_id":doc_id, "source_receipt":receipt, "pages":pages,
                          "method":"pypdf_local_text_extraction_no_OCR", "human_reviewed":False,
                          "quarantine":True, "not_layout_or_label_verified":True}
            extraction_path = root / "quarantine/pdf-text" / (doc_id.split(":")[1] + ".json")
            extraction_sha = write_json(extraction_path, extraction)
            docs.append({**link, "id":doc_id, "kind":"closing_report_pdf", "receipt":receipt,
                         "pages":len(pages), "text_characters":sum(len(p["text"]) for p in pages),
                         "extraction_path":str(extraction_path.relative_to(root)), "extraction_sha256":extraction_sha,
                         "extraction_status":"TEXT_EXTRACTED_UNVERIFIED" if any(p["text"].strip() for p in pages) else "OCR_REQUIRED"})
        except Exception as exc:
            failures.append({"url":link["url"], "cases":link["cases"], "error":type(exc).__name__})
        if (i+1) % 20 == 0:
            print(json.dumps({"pdf_links_attempted":i+1, "listed":len(links), "extracted":len(docs)}), flush=True)
        time.sleep(0.15)
    result = {"schema":1, "linked_documents":len(links), "documents":docs, "failures":failures,
              "coverage":"ALL_EXPLICIT_REPORT_AND_APPENDIX_LINKS_ON_COLLECTED_CASE_PAGES",
              "warning":"An administrative closing report is not proof that the underlying crime was solved",
              "human_reviewed":False, "training":"NOT_RUN", "model_evaluation":"NOT_RUN"}
    write_json(root / "closing-documents.json", result)
    return {"linked":len(links), "downloaded_extracted":len(docs), "failures":len(failures)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    print(json.dumps(collect_documents(parser.parse_args().collection)))
