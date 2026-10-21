import json
import os
import urllib.error
from io import BytesIO

import pytest

from scripts import finish_local_isolation as finish


def test_apply_refuses_nonroot_before_access_or_changes(monkeypatch):
    monkeypatch.setattr(finish.os, "geteuid", lambda: 501)
    with pytest.raises(PermissionError, match="sudo"):
        finish.apply({})


def test_plan_rejects_an_unrelated_directory(tmp_path):
    with pytest.raises(ValueError, match="project isolation run"):
        finish.plan(tmp_path)


def test_different_lock_copies_are_not_a_shared_lock(tmp_path):
    original, copied = tmp_path / "original", tmp_path / "copy"
    original.write_bytes(b"")
    copied.write_bytes(b"")
    original.chmod(0o660)
    with pytest.raises(ValueError, match="shared inode"):
        finish.validate_lock_pair(original, copied, os.getuid(), os.getgid())


def test_shared_lock_must_keep_restrictive_permissions(tmp_path):
    original, copied = tmp_path / "original", tmp_path / "copy"
    original.write_bytes(b"")
    os.link(original, copied)
    original.chmod(0o660)
    finish.validate_lock_pair(original, copied, os.getuid(), os.getgid())
    original.chmod(0o666)
    with pytest.raises(ValueError, match="shared inode"):
        finish.validate_lock_pair(original, copied, os.getuid(), os.getgid())


def test_http503_retains_the_actual_startup_error(tmp_path, monkeypatch):
    private = tmp_path / "runtime/personal-auth"
    private.mkdir(parents=True)
    (private / "auth.json").write_text(json.dumps({"user": "fixture"}))
    (private / "key.txt").write_text("nonsecret-test-value")
    monkeypatch.setattr(finish, "PROJECT", tmp_path)
    def failed(*args, **kwargs):
        raise urllib.error.HTTPError("http://127.0.0.1:8100/ready", 503, "Unavailable", {},
                                     BytesIO(b'{"ready":false,"error":"PermissionError"}'))
    monkeypatch.setattr(finish.urllib.request, "urlopen", failed)
    assert finish.readiness() == {"ready": False, "error": "PermissionError"}


def test_pass_for_a_different_answer_hash_is_rejected():
    with pytest.raises(RuntimeError, match="hash"):
        finish.check_answer({"status": "PASS", "answer_sha256": "wrong"}, {"sha256": "expected"})


def test_account_switch_failure_is_not_answer_denial():
    with pytest.raises(RuntimeError, match="denial"):
        finish.check_answer({"status": "BLOCKED", "answer_sha256": "expected"}, {"sha256": "expected"})


def test_ready_with_a_different_adapter_is_rejected():
    expected = {"model": "4B", "revision": "fixed", "adapter_sha256": "original", "lora_modules": 56}
    with pytest.raises(RuntimeError, match="differs"):
        finish.check_model({**expected, "adapter_loaded": True, "adapter_sha256": "other"}, expected)
    finish.check_model({**expected, "adapter_loaded": True}, expected)
