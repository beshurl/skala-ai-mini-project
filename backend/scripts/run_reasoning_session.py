"""Interactive local administrator session for the predeclared development run.

Run as the evaluator, never with sudo. Passwords go only to sudo's own prompt.
No deployment, migration, training, credential output or adapter promotion.
"""
import argparse
import fcntl
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation import evaluate_reasoning as evaluation
from recase.ledger import digest, file_digest, utc_now
from recase.paths import PROJECT_ROOT
from scripts.diagnose_local_service import LABEL, PLIST, DEPLOY

DIAGNOSTIC = Path(__file__).with_name("diagnose_local_service.py")


def service_identity():
    result = subprocess.run(["/bin/launchctl", "print", "system/" + LABEL], capture_output=True, text=True, timeout=10)
    if result.returncode:
        if "Could not find service" in result.stderr or "Could not find service" in result.stdout:
            return None
        raise RuntimeError("DAEMON_STATE_UNKNOWN")
    match = re.search(r"^\s*pid = (\d+)\s*$", result.stdout, re.M)
    if not match:
        raise RuntimeError("DAEMON_PID_NOT_AVAILABLE")
    pid = int(match[1])
    uid = subprocess.check_output(["/bin/ps", "-p", str(pid), "-o", "uid="], text=True, timeout=5).strip()
    return pid, int(uid)


def plist_metadata():
    info = PLIST.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise PermissionError("PROTECTED_PLIST_CHANGED")
    return {"uid": info.st_uid, "mode": stat.S_IMODE(info.st_mode), "inode": info.st_ino,
            "bytes": info.st_size, "mtime_ns": info.st_mtime_ns}


def prepare(evaluation_path, diagnostic_path, out):
    protocol = evaluation.checked_plan(evaluation_path)
    identity = service_identity()
    if not identity or identity[1] != 499:
        raise PermissionError("EXPECTED_SERVICE_UID499_REQUIRED")
    deployed = sorted((DEPLOY / "app/backend/recase").glob("*.py"))
    if not deployed:
        raise PermissionError("EXISTING_DEPLOYED_CODE_REQUIRED")
    baseline = json.loads(Path(diagnostic_path).read_text())
    observed = baseline["probe"]["database_metadata"]
    if (baseline.get("service_pid") != identity[0] or baseline["probe"].get("uid") != 499
            or baseline["probe"].get("classification") != "READ_ONLY_QUERY_SUCCEEDED"):
        raise PermissionError("MATCHING_USER_TERMINAL_BASELINE_REQUIRED")
    lock = protocol["shared_lock"]
    service_lock = DEPLOY / "app/runtime/model.lock"
    service_info = service_lock.stat()
    if (service_info.st_dev, service_info.st_ino) != (lock["device"], lock["inode"]):
        raise PermissionError("SHARED_SERVICE_MODEL_LOCK_DIFFERS")
    refs = [Path(__file__).absolute(), DIAGNOSTIC, Path(evaluation_path).absolute(), Path(diagnostic_path).absolute(),
            Path(evaluation.__file__).absolute(), *deployed]
    plan = {"kind": "recase-local-reasoning-session-v1", "created_at": utc_now(),
            "operator_uid": os.geteuid(), "expected_pid": identity[0], "service_uid": 499,
            "evaluation_plan": str(Path(evaluation_path).absolute()), "evaluation_plan_sha256": protocol["plan_sha256"],
            "plist_metadata": plist_metadata(), "bound_files": [{"path": str(p), "sha256": file_digest(p)} for p in refs],
            "restore_bound_files": [{"path": str(p), "sha256": file_digest(p)} for p in deployed],
            "model_lock": lock, "service_lock_path": str(service_lock),
            "expected_database": {key: observed[key] for key in ("device", "inode", "uid", "gid", "mode")},
            "actions": ["authenticated fresh UID499 read-only active-job query", "pause same existing daemon only if idle",
                        "sequential base/existing_ft exposed development runs", "restore same unchanged daemon config"],
            "maximum_variant_seconds": 1800, "variants": ["base", "existing_ft"],
            "deployment": False, "training": False, "automatic_retries": 0, "automatic_adapter_promotion": False,
            "restore_model_readiness": "NOT_MEASURED; daemon PID/UID and shared lock are distinct from readiness"}
    plan["plan_sha256"] = digest(plan)
    out = Path(out).absolute();out.mkdir(mode=0o700)
    evaluation.write(out / "session-plan.json", plan)
    return plan


def checked_plan(path):
    path = Path(path).absolute();info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077
            or os.geteuid() == 0 or path.is_symlink()):
        raise PermissionError("RUN_AS_PLAN_OWNING_NONROOT_EVALUATOR")
    plan = json.loads(path.read_text())
    if (plan.get("plan_sha256") != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            or plan.get("operator_uid") != os.geteuid() or plan.get("kind") != "recase-local-reasoning-session-v1"
            or plan.get("variants") != ["base", "existing_ft"] or plan.get("deployment") is not False
            or plan.get("training") is not False or plan.get("automatic_retries") != 0):
        raise ValueError("SESSION_PLAN_CHANGED")
    if plist_metadata() != plan["plist_metadata"]:
        raise PermissionError("PLIST_METADATA_CHANGED")
    if any(file_digest(r["path"]) != r["sha256"] for r in plan["bound_files"]):
        raise PermissionError("SESSION_BOUND_SOURCE_CHANGED")
    if evaluation.checked_plan(plan["evaluation_plan"])["plan_sha256"] != plan["evaluation_plan_sha256"]:
        raise PermissionError("EVALUATION_PLAN_CHANGED")
    return plan


def perform(plan, operations, event):
    """Effectful boundary isolated for failure/restore tests; never infer idle."""
    pause_attempted, original_sha = False, None
    result = {"status": "NOT_RUN", "variants": [], "restore": "NOT_NEEDED"}
    try:
        operations.authenticate()
        original_sha = operations.plist_sha()
        operations.verify_sources()
        if operations.plist_sha() != original_sha:
            raise PermissionError("PLIST_CHANGED_BEFORE_PAUSE")
        state = operations.inspect()
        probe = state.get("probe", {})
        database = probe.get("metadata", {}).get("recase.sqlite3", {})
        if (state.get("service_pid") != plan["expected_pid"] or probe.get("uid") != 499
                or probe.get("euid") != 499 or probe.get("classification") != "READ_ONLY_QUERY_SUCCEEDED"
                or type(probe.get("active_jobs")) is not int or probe["active_jobs"] != 0
                or any(database.get(k) != v for k, v in plan["expected_database"].items())):
            raise RuntimeError("ACTUAL_SERVICE_NOT_CONFIRMED_IDLE")
        event("FRESH_IDLE_CHECK", active_jobs=0, pid=plan["expected_pid"])
        pause_attempted = True
        event("PAUSE_INTENT")
        operations.pause()
        operations.wait_model_idle()
        event("MODEL_LOCK_FREE_AFTER_PAUSE")
        for variant in plan["variants"]:
            operations.verify_sources()
            value = operations.run_variant(variant)
            result["variants"].append(value)
            if (value.get("supervisor_terminated_worker") or value.get("worker_exit_code") not in (0, 3)
                    or value.get("validation_codes", {}).get("GENERAL_MODEL_FAILED")
                    or any(value.get("statuses", {}).get(s) for s in ("FAILED", "CANCELLED", "STALE"))):
                raise RuntimeError("MODEL_RUNTIME_FAILED_NO_AUTOMATIC_RETRY")
        result["status"] = "RUNS_FINISHED_REVIEW_METRICS"
    except (Exception, KeyboardInterrupt) as exc:
        result.update(status="STOPPED_NO_AUTOMATIC_RETRY", error_type=type(exc).__name__)
        event("STOPPED", error_type=type(exc).__name__)
    finally:
        # Intent is set BEFORE bootout. If the command took effect and then
        # raised/interrupted, we still attempt restoration; never start twice.
        if pause_attempted:
            try:
                current = operations.service()
                if current is None:
                    operations.wait_model_idle()
                    operations.authenticate()
                    operations.verify_restore_sources()
                    if operations.plist_sha() != original_sha:
                        raise PermissionError("PLIST_CHANGED_RESTORE_REFUSED")
                    restored = operations.restore()
                    if restored[1] != 499:
                        raise RuntimeError("RESTORED_UID_MISMATCH")
                    result["restore"] = {"state": "SAME_DAEMON_RESTORED", "pid": restored[0], "uid": 499, "model_readiness": "NOT_MEASURED"}
                    event("DAEMON_RESTORED", pid=restored[0], uid=499)
                elif current == (plan["expected_pid"], 499):
                    result["restore"] = "ORIGINAL_DAEMON_STILL_RUNNING_NO_BOOTSTRAP"
                else:
                    raise RuntimeError("EXTERNAL_SERVICE_IDENTITY_CHANGED")
            except (Exception, KeyboardInterrupt) as exc:
                result.update(status="RESTORE_NEEDS_LOCAL_ADMIN", restore={"state": "NOT_CONFIRMED", "error_type": type(exc).__name__})
                event("RESTORE_NOT_CONFIRMED", error_type=type(exc).__name__)
    return result


class MacOperations:
    def __init__(self, plan, plan_path, out, event):
        self.plan, self.path, self.out, self.event = plan, plan_path, out, event

    def authenticate(self):
        print("관리자 암호는 sudo의 이 터미널 프롬프트에만 입력하세요.", flush=True)
        subprocess.run(["/usr/bin/sudo", "-v"], check=True)

    def plist_sha(self):
        value = subprocess.check_output(["/usr/bin/sudo", "-n", "/usr/bin/shasum", "-a", "256", "--", str(PLIST)], text=True).split()[0]
        if not re.fullmatch("[0-9a-f]{64}", value):raise ValueError("INVALID_PLIST_HASH")
        return value

    def inspect(self):
        output = subprocess.check_output(["/usr/bin/sudo", "-n", sys.executable, str(DIAGNOSTIC), "--expected-pid", str(self.plan["expected_pid"])], text=True)
        state = json.loads(output);evaluation.write(self.out / "fresh-uid499-diagnostic.json", state)
        return state

    def verify_sources(self):
        checked_plan(self.path)

    def verify_restore_sources(self):
        # Restore the old verified daemon even if development benchmark code
        # changed. Its own deployment/config and original shared lock must match.
        if plist_metadata() != self.plan["plist_metadata"]:
            raise PermissionError("RESTORE_PLIST_METADATA_CHANGED")
        if any(file_digest(r["path"]) != r["sha256"] for r in self.plan["restore_bound_files"]):
            raise PermissionError("OLD_DEPLOYED_SOURCE_CHANGED")
        self.verify_lock()

    def verify_lock(self):
        expected = self.plan["model_lock"]
        for path in (expected["path"], self.plan["service_lock_path"]):
            actual = Path(path).stat()
            if (actual.st_dev, actual.st_ino) != (expected["device"], expected["inode"]):
                raise PermissionError("ORIGINAL_SHARED_LOCK_CHANGED")

    def pause(self):
        if self.service() != (self.plan["expected_pid"], 499):raise PermissionError("PID_CHANGED_BEFORE_PAUSE")
        subprocess.run(["/usr/bin/sudo", "-n", "/bin/launchctl", "bootout", "system/" + LABEL], check=True)

    def service(self):
        return service_identity()

    def wait_model_idle(self):
        lock = Path(evaluation.LOCK)
        for _ in range(30):
            self.verify_lock()
            try:
                with lock.open("r") as stream:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(stream, fcntl.LOCK_UN)
                if self.service() is None:return
            except BlockingIOError:pass
            time.sleep(1)
        raise RuntimeError("OLD_DAEMON_OR_MODEL_STILL_PRESENT")

    def run_variant(self, variant):
        out = self.out / variant
        command = [sys.executable, str(Path(evaluation.__file__).absolute()), "run", "--plan", self.plan["evaluation_plan"],
                   "--variant", variant, "--backend", "mlx", "--out", str(out)]
        self.event("VARIANT_STARTED", variant=variant)
        with (self.out / (variant + ".log")).open("x") as log:
            process = subprocess.Popen(command, cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                previous = -1
                while process.poll() is None:
                    progress = out / "progress.jsonl"
                    count = len(progress.read_text().splitlines()) if progress.exists() else 0
                    if count != previous:
                        self.event("VARIANT_PROGRESS", variant=variant, recorded_stages=count);previous=count
                    time.sleep(.5)
            except BaseException:
                try:os.killpg(process.pid, signal.SIGINT)
                except ProcessLookupError:pass
                # The benchmark supervisor handles interruption by stopping its
                # own model worker. Failure to exit keeps restoration blocked.
                process.wait(timeout=30)
                raise
        value = json.loads((out / "metrics.json").read_text())
        self.event("VARIANT_FINISHED", variant=variant, valid_stages=value["valid_stages"], exit_code=process.returncode)
        return value

    def restore(self):
        subprocess.run(["/usr/bin/sudo", "-n", "/bin/launchctl", "bootstrap", "system", str(PLIST)], check=True)
        for _ in range(30):
            try:
                value = self.service()
                if value:return value
            except RuntimeError:pass
            time.sleep(1)
        raise RuntimeError("RESTORED_DAEMON_NOT_OBSERVED")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true");parser.add_argument("--execute", action="store_true")
    parser.add_argument("--evaluation-plan");parser.add_argument("--diagnostic");parser.add_argument("--plan");parser.add_argument("--out")
    args = parser.parse_args()
    if args.prepare and (args.execute or args.plan or not args.evaluation_plan or not args.diagnostic or not args.out):
        parser.error("--prepare requires --evaluation-plan, --diagnostic and --out; cannot combine with --execute/--plan")
    if not args.prepare and not args.plan:
        parser.error("--plan is required for checking or execution")
    if args.prepare:
        value = prepare(args.evaluation_plan, args.diagnostic, args.out)
        print(json.dumps({"status": "PREPARED_NOT_EXECUTED", "expected_pid": value["expected_pid"], "plan_sha256": value["plan_sha256"]}))
        return 0
    plan = checked_plan(args.plan)
    if not args.execute:
        print(json.dumps({"status": "SOURCE_PLAN_CHECK_PASS", "model_calls": 0, "service_changes": 0}))
        return 0
    if not sys.stdin.isatty():raise PermissionError("EXECUTE_FROM_LOCAL_USER_TERMINAL_NOT_CHAT")
    if service_identity() != (plan["expected_pid"], 499):raise PermissionError("ORIGINAL_SERVICE_CHANGED")
    out = Path(args.plan).absolute().parent / ("execution-" + secrets_id())
    out.mkdir(mode=0o700);evaluation.write(out / "session-plan-copy.json", plan)
    def event(name, **fields):
        row = {"at": utc_now(), "event": name, **fields}
        with (out / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n");stream.flush();os.fsync(stream.fileno())
        print(json.dumps(row, ensure_ascii=False), flush=True)
    result = perform(plan, MacOperations(plan, args.plan, out, event), event)
    if len(result["variants"]) == 2:
        try:
            comparison = evaluation.compare([out / "base/metrics.json", out / "existing_ft/metrics.json"])
            evaluation.write(out / "comparison.json", comparison)
            result["comparison"] = "EXPOSED_DEVELOPMENT_ONLY_COMPLETE"
        except (ValueError, KeyError, OSError):
            result["comparison"] = "REFUSED_INCOMPLETE_OR_UNMATCHED"
            evaluation.write(out / "comparison-refused.json", {"status": result["comparison"], "independent_final_accuracy": "NOT_MEASURED"})
    result.update(finished_at=utc_now(), training_runs=0, deployment=False, automatic_adapter_promotion=False)
    evaluation.write(out / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(out / "result.json"), "restore": result["restore"]}, ensure_ascii=False))
    return 0 if result["status"] == "RUNS_FINISHED_REVIEW_METRICS" else 2


def secrets_id():
    import secrets
    return secrets.token_hex(8)


if __name__ == "__main__":
    raise SystemExit(main())
