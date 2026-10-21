"""Public document collection. Never imports into the service or trains a model."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from recase.ledger import append_record, read_ledger, utc_now

AGENT = "RECASE-local-research/0.1"
HOSTS = frozenset({"api.fbi.gov", "www.fbi.gov", "archives.fbi.gov",
                   "www.safe182.go.kr", "archives.go.kr", "www.archives.go.kr",
                   "namus.nij.ojp.gov", "open.law.go.kr", "www.contracosta.ca.gov",
                   "www.justice.gov", "www.mass.gov"})
MAX_BYTES = 8 * 1024 * 1024
MAX_PDF_BYTES = 64 * 1024 * 1024


def validate_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username
            or parsed.password or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("Only configured public HTTPS sources are permitted")
    # This collector deliberately has no authenticated mode.
    if re.search(r"(?:^|[?&])(?:key|token|password|secret|oc|authkey|api_key)=", parsed.query and "?" + parsed.query or "", re.I):
        raise ValueError("Authenticated source URLs are not accepted")
    return url


def private_directory(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink storage paths are refused")
    missing = []
    parent = path
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
    stat = path.stat()
    if stat.st_uid != os.geteuid() or stat.st_mode & 0o077:
        raise PermissionError("Collection directories must be private to their owner")
    return path


def write_new(path, value):
    """Exclusive writes: an existing dataset or result is never replaced."""
    path = Path(path)
    private_directory(path.parent)
    data = value if isinstance(value, bytes) else value.encode("utf8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    return write_new(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class PublicCollector:
    def __init__(self, root, client=None):
        self.root = private_directory(root)
        self.raw = private_directory(self.root / "raw")
        private_directory(self.root / "logs")
        self.ledger = self.root / "logs" / "requests.jsonl"
        self.client = client or httpx.Client(timeout=20, follow_redirects=False,
                                            trust_env=False, headers={"User-Agent": AGENT})
        self.robots = {}

    def _save_response(self, url, attempt, response, data):
        sha = hashlib.sha256(data).hexdigest()
        extension = ".pdf" if "application/pdf" in response.headers.get("content-type", "").lower() else ".bin"
        target = self.raw / (sha + extension)
        try:
            write_new(target, data)
        except FileExistsError:
            if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError("Existing raw object integrity failure")
        row = {"url": url, "attempt": attempt, "retrieved_at": utc_now(),
               "http_status": response.status_code, "content_type": response.headers.get("content-type", ""),
               "bytes": len(data), "sha256": sha, "path": str(target.relative_to(self.root))}
        append_record(self.ledger, row)
        return row

    def _request(self, url, max_bytes=MAX_BYTES):
        validate_url(url)
        for attempt in range(1, 3):
            try:
                current = url
                for redirect in range(4):
                    with self.client.stream("GET", current) as response:
                        if response.is_redirect:
                            if redirect == 3:
                                raise ValueError("Redirect limit")
                            next_url = validate_url(urljoin(current, response.headers["location"]))
                            if urlsplit(next_url).netloc != urlsplit(url).netloc:
                                raise ValueError("Cross-origin redirect requires a separate source entry")
                            current = next_url
                            continue
                        chunks, size = [], 0
                        for block in response.iter_bytes():
                            size += len(block)
                            if size > max_bytes:
                                raise ValueError("Response exceeds text collection limit")
                            chunks.append(block)
                        data = b"".join(chunks)
                        row = self._save_response(url, attempt, response, data)
                        if response.status_code == 429 or response.status_code >= 500:
                            if attempt == 1:
                                time.sleep(1)
                                break
                        return data, row
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                append_record(self.ledger, {"url": url, "attempt": attempt,
                                           "error": type(exc).__name__, "retrieved_at": utc_now()})
                if attempt == 2 or isinstance(exc, (ValueError, KeyError)):
                    raise
                time.sleep(1)
        raise RuntimeError("Source unavailable after two attempts")

    def fetch(self, url, allow_pdf=False):
        validate_url(url)
        origin = "https://" + urlsplit(url).netloc
        if origin not in self.robots:
            data, receipt = self._request(origin + "/robots.txt")
            status = receipt["http_status"]
            parser = RobotFileParser(origin + "/robots.txt")
            if status == 200:
                parser.parse(data.decode("utf8", "replace").splitlines())
            elif status in (404, 410):
                parser.parse(["User-agent: *", "Disallow:"])
            else:
                raise ValueError("Cannot establish public crawler access")
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(AGENT, url):
            append_record(self.ledger, {"url": url, "error": "ROBOTS_DISALLOWED"})
            raise ValueError("Public crawler access disallowed")
        data, receipt = self._request(url, MAX_PDF_BYTES if allow_pdf else MAX_BYTES)
        if receipt["http_status"] != 200:
            raise ValueError("Public source did not return HTTP 200")
        accepted = ("text/", "json", "xml", "application/pdf") if allow_pdf else ("text/", "json", "xml")
        if not any(t in receipt["content_type"].lower() for t in accepted):
            raise ValueError("Only public text responses are accepted")
        return data, receipt


class Element:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def descendants(self):
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.descendants()

    def text(self):
        if self.tag in {"script", "style", "noscript", "nav", "header", "footer"}:
            return ""
        return " ".join(c.text() if isinstance(c, Element) else c for c in self.children)


class TextDocument(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def nodes(self, tag=None):
        return [n for n in self.root.descendants() if tag is None or n.tag == tag]

    def metadata(self):
        return {n.attrs.get("property", n.attrs.get("name", "")): n.attrs.get("content", "")
                for n in self.nodes("meta")}


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def decode_text(data, content_type=""):
    """Honor declared HTML encoding, with a visible fallback for legacy official pages."""
    header = re.search(r"charset\s*=\s*[\"']?([\w-]+)", content_type, re.I)
    meta = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", data[:8192], re.I)
    declared = header.group(1) if header else meta.group(1).decode("ascii") if meta else None
    candidates = [declared] if declared else []
    candidates += ["utf8", "windows-1252"]
    for encoding in candidates:
        try:
            return data.decode(encoding), encoding
        except (UnicodeError, LookupError):
            continue
    return data.decode("utf8", "replace"), "utf8-replacement-REVIEW_REQUIRED"


def mask_contacts(text):
    """Partial automated masking only. Does not certify anonymization."""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d() .-]{6,}\d)(?!\w)", "[NUMBER_REVIEW]", text)
    return text


def verify_receipts(root):
    root = Path(root)
    rows = read_ledger(root / "logs/requests.jsonl")
    for row in rows:
        receipt = row["payload"]
        if "path" not in receipt:
            continue
        relative = Path(receipt["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Raw receipt path escapes collection")
        target = root / relative
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError("Raw receipt symlink")
        if hashlib.sha256(target.read_bytes()).hexdigest() != receipt["sha256"]:
            raise ValueError("Raw receipt hash mismatch")
    return rows
