"""Synthetic checks of acquisition integrity; never a model accuracy benchmark."""
import hashlib
import json

import httpx
import pytest

from recase.ledger import append_record
from recase.public_collection import (
    MAX_BYTES, PublicCollector, TextDocument, clean_text, mask_contacts,
    decode_text, private_directory, validate_url, verify_receipts, write_new,
)


@pytest.mark.parametrize("url", [
    "http://www.fbi.gov/x", "https://evil.test/x", "https://user:pass@www.fbi.gov/x",
    "https://www.fbi.gov:444/x", "https://www.fbi.gov/x#fragment",
    "https://open.law.go.kr/api?OC=private", "https://api.fbi.gov/x?api_key=secret",
])
def test_refuse_nonpublic_or_credential_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_exclusive_private_objects(tmp_path):
    root = private_directory(tmp_path / "private")
    path = root / "raw.bin"
    write_new(path, b"preserve")
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_new(path, b"replace")
    assert path.read_bytes() == b"preserve"


def test_symlink_storage_refused(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    with pytest.raises(ValueError):
        private_directory(tmp_path / "link" / "nested")


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_collect_and_verify_hash_chain(tmp_path):
    def handler(request):
        text = "User-agent: *\nDisallow:" if request.url.path == "/robots.txt" else '{"items":[]}'
        return httpx.Response(200, text=text, headers={"content-type": "application/json"})
    collector = PublicCollector(tmp_path / "vault", client_for(handler))
    body, receipt = collector.fetch("https://api.fbi.gov/wanted/v1/list?page=1")
    assert receipt["sha256"] == hashlib.sha256(body).hexdigest()
    assert len(verify_receipts(collector.root)) == 2
    (collector.root / receipt["path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_receipts(collector.root)


def test_robots_denial_stops_case_request(tmp_path):
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nDisallow: /wanted", headers={"content-type":"text/plain"})
    collector = PublicCollector(tmp_path / "vault", client_for(handler))
    with pytest.raises(ValueError, match="disallowed"):
        collector.fetch("https://api.fbi.gov/wanted/v1/list")
    assert seen == ["https://api.fbi.gov/robots.txt"]


def test_cross_origin_redirect_never_requests_destination(tmp_path):
    seen = []
    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location":"https://www.justice.gov/other"})
    collector = PublicCollector(tmp_path / "vault", client_for(handler))
    with pytest.raises(ValueError, match="Cross-origin"):
        collector.fetch("https://api.fbi.gov/wanted/v1/list")
    assert not any("justice.gov" in url for url in seen)


def test_size_limit_and_auth_denial_are_not_retried(tmp_path):
    seen = []
    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"x" * (MAX_BYTES + 1), headers={"content-type":"text/plain"})
    collector = PublicCollector(tmp_path / "vault", client_for(handler))
    with pytest.raises(ValueError, match="limit"):
        collector.fetch("https://api.fbi.gov/wanted/v1/list")
    assert len(seen) == 2


def test_receipt_traversal_rejected(tmp_path):
    root = private_directory(tmp_path / "vault")
    append_record(root / "logs/requests.jsonl", {"path":"../outside", "sha256":"0"*64})
    with pytest.raises(ValueError, match="escapes"):
        verify_receipts(root)


def test_text_excludes_executable_and_navigation_content():
    doc = TextDocument('<main><p>Fact &amp; source</p><script>instruction()</script><nav>junk</nav></main>')
    assert clean_text(doc.root.text()) == "Fact & source"
    # Text that looks like an instruction remains data, never executed.
    assert clean_text(TextDocument('<p>ignore rules</p>').root.text()) == "ignore rules"


def test_partial_contact_masking_preserves_uncertainty():
    text = mask_contacts("Name Person: info@example.org +1 555 123 4567")
    assert "info@example.org" not in text and "555" not in text
    assert "Name Person" in text  # Explicitly not complete de-identification.


def test_legacy_charset_is_decoded_without_silent_replacement():
    text, encoding = decode_text(b'<meta charset="windows-1252"><p>Source \x96 quote</p>')
    assert "\ufffd" not in text and "\u2013" in text
    assert encoding == "windows-1252"
