"""Local-only, resumable ingestion to quarantine; no network/API or approval bypass."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.ignored = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def clean(text):
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in [
        (r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)", "[전화번호]"),
        (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[이메일]"),
        (r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)", "[주민등록번호]")]:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def ingest(root, manifest_path, output, limit=100, dry_run=False, resume=False):
    root, output = Path(root).resolve(), Path(output)
    if not root.is_dir() or not 1 <= limit <= 1000:
        raise ValueError("Invalid input directory or limit")
    manifest = json.loads(Path(manifest_path).read_text())
    docs = manifest.get("documents", [])
    if len({x["file"] for x in docs}) != len(docs):
        raise ValueError("Duplicate manifest entries")
    if output.exists() and not resume:
        raise FileExistsError("Existing output requires --resume; overwrite is forbidden")
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "quarantined.jsonl"
    existing = [json.loads(x) for x in rows_path.read_text().splitlines()] if rows_path.is_file() else []
    seen = {r["raw_sha256"] for r in existing}
    clean_seen = {r.get("clean_sha256") for r in existing}
    results = {"source_type": manifest.get("source_type", "user_supplied_local"), "dry_run": dry_run, "collected": 0, "quarantined": 0, "duplicates": 0, "denied": 0, "failed": 0, "attempted": 0}
    for item in docs[:limit]:
        results["attempted"] += 1
        filename = item["file"]
        path = (root / filename).resolve()
        if Path(filename).name != filename or path.parent != root or Path(root / filename).is_symlink():
            results["denied"] += 1
            continue
        if item.get("permissions", {}).get("processing") is not True or not item.get("rights_basis", "").strip():
            results["denied"] += 1
            continue
        if not path.is_file() or path.suffix.lower() not in (".txt", ".html", ".htm", ".pdf") or path.stat().st_size > MAX_BYTES:
            results["failed"] += 1
            continue
        if dry_run:
            results["collected"] += 1
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen:
            results["duplicates"] += 1
            continue
        record = {"doc_id": digest[:20], "raw_sha256": digest, "source_file": filename,
                  "source_type": results["source_type"], "source_url": item.get("source_url"),
                  "collected_at": datetime.now(timezone.utc).isoformat(), "rights_basis": item["rights_basis"],
                  "permissions": item["permissions"], "state": "RAW", "review_required": True,
                  "privacy_review": {"human_reviewed": False}, "label_review": {"human_reviewed": False}}
        try:
            if path.suffix.lower() == ".pdf":
                from pypdf import PdfReader
                pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(PdfReader(path).pages)]
                encoding = None
            else:
                try:
                    text, encoding = raw.decode("utf-8-sig"), "utf-8-sig"
                except UnicodeDecodeError:
                    text, encoding = raw.decode("cp949"), "cp949"
                if path.suffix.lower() in (".html", ".htm"):
                    parser = TextHTML(); parser.feed(text); text = "".join(parser.parts)
                pages = [(1, text)]
            record["state"] = "PARSED"
            spans = [{"page": page, "text": clean(text)} for page, text in pages]
            joined = "\n\n".join(s["text"] for s in spans)
            cleaned_hash = hashlib.sha256(joined.encode()).hexdigest()
            if cleaned_hash in clean_seen:
                results["duplicates"] += 1
                seen.add(digest)
                continue
            cursor = 0
            for span in spans:
                span.update(start=cursor, end=cursor + len(span["text"]))
                cursor = span["end"] + 2
            record.update(state="QUARANTINED", text=joined, spans=spans, encoding=encoding,
                          clean_sha256=cleaned_hash, cleaning_version="nfc-patterns-v2",
                          quarantine_reason="HUMAN_PRIVACY_AND_PURPOSE_REVIEW_REQUIRED" if len(joined) >= 100 else "LOW_TEXT_QUALITY_OR_OCR_REQUIRED")
            clean_seen.add(cleaned_hash)
            results["collected"] += 1
            results["quarantined"] += 1
        except Exception as error:
            record.update(state="QUARANTINED", quarantine_reason="PARSE_FAILED", error_type=type(error).__name__)
            results["failed"] += 1
        with rows_path.open("a", encoding="utf8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
        seen.add(digest)
    if not dry_run:
        report = output / ("report-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        with report.open("x") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    return results
