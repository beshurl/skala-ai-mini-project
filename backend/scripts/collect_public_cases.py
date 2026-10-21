#!/usr/bin/env python3
"""Collect a defined public snapshot into a new external, private data directory."""
import argparse
import json
import math
import re
import time
from pathlib import Path

from recase.ledger import utc_now
from recase.public_collection import PublicCollector, TextDocument, write_json


SOURCES = [
    ("fbi_api_docs", "documentation", "https://www.fbi.gov/wanted/api"),
    ("fbi_reuse", "policy", "https://www.fbi.gov/privacy-policy"),
    ("safe182_list", "public_missing_list", "https://www.safe182.go.kr/home/lcm/lcmMssList.do"),
    ("safe182_auth", "authentication_docs", "https://www.safe182.go.kr/home/api/authKey1Create.do"),
    ("namus_faq", "authentication_docs", "https://namus.nij.ojp.gov/frequently-asked-questions"),
    ("law_api_docs", "authentication_docs", "https://open.law.go.kr/LSO/openApi/guideList.do"),
    ("law_prec_docs", "authentication_docs", "https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=mobPrecListGuide"),
    ("archives_01", "catalog_only", "https://archives.go.kr/next/newsearch/showDetailPopup.do?rc_code=1310377&rc_rfile_no=201103616419&rc_ritem_no=000000000007&sitePage=0-0-0"),
    ("archives_02", "catalog_only", "https://www.archives.go.kr/next/newsearch/showDetailPopup.do?rc_code=1310377&rc_rfile_no=202010421912&rc_ritem_no=000000000002&sitePage=0-0-0"),
    ("golden_pre_updated", "case_source", "https://www.fbi.gov/contact-us/field-offices/sacramento/news/press-releases/fbi-announces-50-000-reward-and-national-campaign-to-identify-east-area-rapist-golden-state-killer"),
    ("golden_sentence", "case_source", "https://www.contracosta.ca.gov/m/newsflash/Archive/Item/2380?arcId=7624"),
    ("dunes_identified", "case_source", "https://www.fbi.gov/contact-us/field-offices/boston/news/press-releases/lady-of-the-dunes-identified"),
    ("ricks_retrospective", "case_source", "https://www.fbi.gov/news/stories/james-ricks-cold-case-solved"),
    ("houston_retrospective", "case_source", "https://www.fbi.gov/news/stories/houston-cold-case-solved"),
    ("thirty_year_retrospective", "case_source", "https://www.fbi.gov/news/stories/30-year-old-murder-solved"),
    ("tinsley_pre", "case_source", "https://archives.fbi.gov/archives/news/stories/2009/april/amw_041409-part-2"),
    ("seale_charged", "case_source", "https://archives.fbi.gov/archives/news/stories/2007/january/seale012507"),
    ("seale_indictment", "case_source", "https://www.justice.gov/archive/opa/pr/2007/January/07_crt_043.html"),
    ("seale_verdict", "case_source", "https://www.justice.gov/archive/opa/pr/2007/June/07_crt_431.html"),
    ("doj_closing_list", "catalog_only", "https://www.justice.gov/crt/civil-rights-division-emmett-till-act-cold-case-closing-memoranda"),
]


def collect(root):
    root = Path(root).absolute()
    project = Path(__file__).resolve().parents[2]
    if root == project or project in root.parents:
        raise ValueError("Store source data outside the code project")
    if (root / "collection.json").exists():
        raise FileExistsError("Use a new collection directory; existing collections are immutable")
    collector = PublicCollector(root)
    start, pages, sources, failures = utc_now(), [], [], []
    expected = None
    for page in range(1, 1001):
        url = f"https://api.fbi.gov/wanted/v1/list?page={page}"
        try:
            data, receipt = collector.fetch(url)
            obj = json.loads(data)
            if obj.get("page") != page or not isinstance(obj.get("items"), list):
                raise ValueError("Unexpected public API page schema")
            if expected is None:
                expected = obj["total"]
                if not isinstance(expected, int) or not 0 <= expected <= 20000:
                    raise ValueError("Source total outside declared collection budget")
            pages.append({"page": page, "total": obj["total"], "items": len(obj["items"]), "receipt": receipt})
            if page % 10 == 0:
                print(json.dumps({"fbi_pages_collected": page, "reported_total": expected}), flush=True)
            if not obj["items"] or page >= math.ceil(expected / 20):
                break
        except Exception as exc:
            failures.append({"source": "fbi_api", "page": page, "error": type(exc).__name__})
            break
        time.sleep(0.15)
    # Availability and policy documents, never credentials or account creation.
    for key, kind, url in SOURCES:
        try:
            data, receipt = collector.fetch(url)
            sources.append({"id": key, "kind": kind, "url": url, "receipt": receipt})
            print(json.dumps({"source": key, "status": "COLLECTED"}), flush=True)
        except Exception as exc:
            failures.append({"source": key, "url": url, "error": type(exc).__name__})
            print(json.dumps({"source": key, "status": "UNAVAILABLE", "error": type(exc).__name__}), flush=True)
    result = {"schema": 1, "started_at": start, "finished_at": utc_now(),
              "scope": "FBI public wanted API enumerated pages + explicit official source list; not all worldwide cold cases",
              "fbi_reported_total_start": expected, "fbi_pages": pages, "sources": sources,
              "failures": failures, "human_reviewed": False,
              "quarantine": True, "training": "NOT_RUN", "model_evaluation": "NOT_RUN"}
    write_json(root / "collection.json", result)
    return {"fbi_pages": len(pages), "source_documents": len(sources), "failures": len(failures)}


def collect_closing_memos(root, index_manifest):
    """Enumerate only the public HTML case links on the official closing-memo list."""
    root = Path(root).absolute()
    project = Path(__file__).resolve().parents[2]
    if root == project or project in root.parents:
        raise ValueError("Store source data outside the code project")
    target = root / "closing-memos-canonical.json"
    if target.exists():
        raise FileExistsError("Existing closing-memo snapshots cannot be replaced")
    manifest = json.loads(Path(index_manifest).read_text())
    index = next(s for s in manifest["sources"] if s["id"] == "doj_closing_list")
    raw = root / index["receipt"]["path"]
    import hashlib
    if hashlib.sha256(raw.read_bytes()).hexdigest() != index["receipt"]["sha256"]:
        raise ValueError("Catalog hash mismatch")
    collector = PublicCollector(root)
    first_data, first_receipt = collector.fetch(index["url"] + "?sort_by=title&page=0")
    doc = TextDocument(first_data.decode("utf8"))
    def case_links(document):
        return {"https://www.justice.gov" + a.attrs["href"] for a in document.nodes("a")
                if a.attrs.get("href", "").startswith("/crt/case/")}
    urls = case_links(doc)
    total_match = re.search(r"([\d,]+)\s+Results", doc.root.text())
    expected = int(total_match.group(1).replace(",", "")) if total_match else None
    if expected is None or not 1 <= expected <= 300 or not urls:
        raise ValueError("Unexpected public catalog size")
    failures, index_pages = [], [first_receipt]
    page_count = math.ceil(expected / len(urls))
    for page in range(1, page_count):
        page_url = index["url"] + f"?sort_by=title&page={page}"
        data, receipt = collector.fetch(page_url)
        urls.update(case_links(TextDocument(data.decode("utf8", "replace"))))
        index_pages.append(receipt)
        time.sleep(0.15)
    # Previously acquired first-page objects remain immutable and can be reused.
    previous = json.loads((root / "closing-memos.json").read_text()) if (root / "closing-memos.json").exists() else {"sources":[]}
    existing = {s["url"]:s for s in previous["sources"]}
    sources = []
    for i, url in enumerate(sorted(urls)):
        if url in existing:
            sources.append({**existing[url], "id":"doj:" + hashlib.sha256(url.encode()).hexdigest()[:20]})
            continue
        try:
            _, receipt = collector.fetch(url)
            sources.append({"id": "doj:" + hashlib.sha256(url.encode()).hexdigest()[:20], "kind": "closure_memo",
                            "url": url, "receipt": receipt})
        except Exception as exc:
            failures.append({"source": url, "error": type(exc).__name__})
        if (i + 1) % 20 == 0:
            print(json.dumps({"doj_links_attempted": i + 1, "listed": len(urls), "collected": len(sources)}), flush=True)
        time.sleep(0.15)
    write_json(target, {"index": index, "index_pages":index_pages,
                                              "reported_total":expected, "unique_listed":len(urls),
                                              "coverage_complete":len(urls)==expected and not failures,
                                              "listed": len(urls),
                                              "sources": sources, "failures": failures,
                                              "warning": "Closing memo does not mean a crime was solved or a person convicted"})
    return {"listed": len(urls), "collected": len(sources), "failed": len(failures)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--closing-index", type=Path, help="Existing collection manifest containing doj_closing_list")
    args = parser.parse_args()
    print(json.dumps(collect_closing_memos(args.output, args.closing_index)
                     if args.closing_index else collect(args.output)))
