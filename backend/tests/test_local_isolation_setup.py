"""No administrator mutation is performed by these tests."""
from pathlib import Path

import pytest

from scripts import configure_local_isolation as setup


def test_apply_refuses_nonroot_before_any_mutation(monkeypatch):
    monkeypatch.setattr(setup.os, "geteuid", lambda: 501)
    with pytest.raises(PermissionError, match="administrator"):
        setup.apply({})


def test_plan_rejects_foreign_output_directory(tmp_path):
    with pytest.raises(ValueError, match="outputs/runs"):
        setup.plan(tmp_path, 1)


def test_clone_is_independent_copy_and_preserves_bytes(tmp_path):
    original, copied = tmp_path / "source", tmp_path / "copy"
    original.write_bytes(b"immutable original")
    setup.clone_copy(original, copied)
    assert copied.read_bytes() == original.read_bytes()
    assert copied.stat().st_ino != original.stat().st_ino
    copied.write_bytes(b"changed copy")
    assert original.read_bytes() == b"immutable original"


def test_no_restore_when_no_cutover_started(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No process command is allowed before cutover")
    monkeypatch.setattr(setup.subprocess, "run", forbidden)
    monkeypatch.setattr(setup.subprocess, "Popen", forbidden)
    setup.restore_original({})


def test_public_model_lock_directory_survives_private_umask(tmp_path):
    import os
    previous = os.umask(0o077)
    try:
        runtime = tmp_path / "runtime"
        setup.create_model_runtime(runtime)
    finally:
        os.umask(previous)
    assert runtime.stat().st_mode & 0o777 == 0o755


def test_keyboard_interrupt_requests_original_service_recovery(monkeypatch):
    import sys
    cfg = {"cutover_started": True}
    called = []
    monkeypatch.setattr(sys, "argv", ["setup", "--run", "test", "--service-pid", "1", "--apply"])
    monkeypatch.setattr(setup, "plan", lambda *args: cfg)
    def interrupted(configuration):
        raise KeyboardInterrupt()
    monkeypatch.setattr(setup, "apply", interrupted)
    monkeypatch.setattr(setup, "restore_original", lambda configuration: called.append(configuration))
    with pytest.raises(KeyboardInterrupt):
        setup.main()
    assert called == [cfg]
