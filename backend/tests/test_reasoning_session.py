"""Control-plane simulation only: no sudo, launchctl, model or live DB."""
import pytest

from scripts import run_reasoning_session as session


BASELINE = {"device": 1, "inode": 2, "uid": 499, "gid": 499, "mode": "0o600"}
PLAN = {"expected_pid": 1234, "variants": ["base", "existing_ft"], "expected_database": BASELINE}


class Operations:
    def __init__(self, active=0, pause_error=False, model_error=False, source_error=False, plist_change=False):
        self.active, self.pause_error, self.model_error = active, pause_error, model_error
        self.source_error, self.plist_change = source_error, plist_change
        self.current = (1234, 499)
        self.calls = []
        self.verifications = 0

    def authenticate(self):self.calls.append("authenticate")
    def plist_sha(self):return "changed" if self.plist_change and self.current is None else "original"
    def inspect(self):
        self.calls.append("inspect")
        return {"service_pid": 1234, "probe": {"uid": 499, "euid": 499, "classification": "READ_ONLY_QUERY_SUCCEEDED",
                "active_jobs": self.active, "metadata": {"recase.sqlite3": BASELINE}}}
    def verify_sources(self):
        self.verifications += 1
        if self.source_error and self.verifications > 1:raise PermissionError("DEVELOPMENT_CODE_CHANGED")
    def verify_restore_sources(self):self.calls.append("old_deployment_verified")
    def pause(self):
        self.calls.append("pause");self.current = None
        if self.pause_error:raise RuntimeError("COMMAND_FAILED_AFTER_EFFECT")
    def wait_model_idle(self):self.calls.append("idle")
    def service(self):return self.current
    def restore(self):
        self.calls.append("restore");self.current = (5678, 499)
        return self.current
    def run_variant(self, variant):
        self.calls.append(variant)
        return {"variant": variant, "worker_exit_code": 3 if self.model_error else 0,
                "validation_codes": {"GENERAL_MODEL_FAILED": 1} if self.model_error else {}}


def run(operations):
    events = []
    result = session.perform(PLAN, operations, lambda name, **kw: events.append((name, kw)))
    return result, events


def test_active_jobs_never_pause_or_run():
    ops = Operations(active=1);result, _ = run(ops)
    assert result["status"] == "STOPPED_NO_AUTOMATIC_RETRY"
    assert "pause" not in ops.calls and "base" not in ops.calls and "restore" not in ops.calls


def test_pause_error_after_effect_still_restores():
    ops = Operations(pause_error=True);result, _ = run(ops)
    assert result["restore"]["state"] == "SAME_DAEMON_RESTORED"
    assert ops.calls.count("restore") == 1 and "base" not in ops.calls


def test_runtime_failure_stops_next_variant_and_restores():
    ops = Operations(model_error=True);result, _ = run(ops)
    assert "base" in ops.calls and "existing_ft" not in ops.calls
    assert result["restore"]["pid"] == 5678
    assert result["restore"]["model_readiness"] == "NOT_MEASURED"


def test_development_code_change_does_not_prevent_safe_old_daemon_restore():
    ops = Operations(source_error=True);result, _ = run(ops)
    assert result["status"] == "STOPPED_NO_AUTOMATIC_RETRY"
    assert "old_deployment_verified" in ops.calls and "restore" in ops.calls


def test_job_timeout_without_result_stops_next_variant_and_restores():
    ops = Operations()
    def timeout(variant):
        ops.calls.append(variant)
        return {"variant": variant, "worker_exit_code": 3, "statuses": {"FAILED": 1}, "validation_codes": {}}
    ops.run_variant = timeout
    result, _ = run(ops)
    assert "base" in ops.calls and "existing_ft" not in ops.calls
    assert result["status"] == "STOPPED_NO_AUTOMATIC_RETRY" and "restore" in ops.calls


def test_changed_config_is_not_bootstrapped():
    ops = Operations(plist_change=True);result, _ = run(ops)
    assert "restore" not in ops.calls
    assert result["status"] == "RESTORE_NEEDS_LOCAL_ADMIN"


def test_success_runs_variants_once_and_restarts_same_daemon():
    ops = Operations();result, events = run(ops)
    assert result["status"] == "RUNS_FINISHED_REVIEW_METRICS"
    assert ops.calls.count("base") == ops.calls.count("existing_ft") == ops.calls.count("restore") == 1
    assert [name for name, _ in events].index("PAUSE_INTENT") < [name for name, _ in events].index("DAEMON_RESTORED")
