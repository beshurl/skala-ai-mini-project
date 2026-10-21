"""Finish this project's interrupted service cutover without recreating accounts.

Only repairs the root-owned public model-lock directory, restarts the existing
verified daemon if needed, and verifies real answer-file isolation. Run --apply
from the user's authenticated local terminal. Does not approve data or train.
"""
import argparse
import base64
import hashlib
import json
import os
import plistlib
import pwd
import re
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT = Path(__file__).resolve().parents[2]
SERVICE = "_recase_service"


def now():
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()


def plan(value):
    run = Path(value).resolve(strict=True)
    if not run.is_relative_to(PROJECT / "outputs/runs"):
        raise ValueError("Existing project isolation run required")
    cfg = json.loads((run / "administrator-change-plan.json").read_text())
    deploy = Path("/Users/Shared") / ("RECASE-isolated-" + run.name.rsplit("-", 1)[-1])
    if cfg["run"] != str(run) or cfg["deployment"] != str(deploy) or cfg["service"] != SERVICE:
        raise ValueError("Deployment identity changed")
    account = pwd.getpwnam(SERVICE)
    if (account.pw_uid != cfg["service_uid"] or account.pw_gid != cfg["service_gid"]
            or account.pw_uid in (0, cfg["operator_uid"]) or account.pw_shell != "/usr/bin/false"
            or account.pw_dir != str(deploy / "home")):
        raise ValueError("Existing service account does not match the approved deployment")
    phases = {json.loads(line)["phase"] for line in (run / "admin-progress.jsonl").read_text().splitlines()}
    if not {"deployment_prepared", "isolated_service_bootstrapped"}.issubset(phases):
        raise ValueError("This is not the recorded interrupted activation")
    if "admin" in subprocess.check_output(["/usr/bin/id", "-Gn", SERVICE], text=True).split():
        raise ValueError("A nonadmin service account is required")
    cfg["launchd_label"] = "com.recase.isolated." + deploy.name.rsplit("-", 1)[-1]
    cfg["launchd_plist"] = "/Library/LaunchDaemons/" + cfg["launchd_label"] + ".plist"
    return cfg


def root_path(path, directory=False):
    info = Path(path).lstat()
    if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
        raise ValueError("Expected an immutable root-owned deployment path: " + str(path))
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ValueError("Expected a deployment directory")
    return info


def validate_lock_pair(original, copied, uid, gid):
    original_info, copied_info = original.lstat(), copied.lstat()
    if (not stat.S_ISREG(original_info.st_mode) or not stat.S_ISREG(copied_info.st_mode)
            or (original_info.st_dev, original_info.st_ino) != (copied_info.st_dev, copied_info.st_ino)
            or original_info.st_uid != uid or original_info.st_gid != gid
            or stat.S_IMODE(original_info.st_mode) != 0o660):
        raise ValueError("The original and deployed model locks must be the approved shared inode")


def readiness():
    auth = json.loads((PROJECT / "runtime/personal-auth/auth.json").read_text())
    key = (PROJECT / "runtime/personal-auth/key.txt").read_text().strip()
    value = "Basic " + base64.b64encode((auth["user"] + ":" + key).encode()).decode()
    request = urllib.request.Request("http://127.0.0.1:8100/ready", headers={"Authorization": value})
    try:
        response = urllib.request.urlopen(request, timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    except OSError:
        return None
    with response:
        try:
            return json.load(response)
        except ValueError:
            return None


def daemon_state(cfg):
    response = subprocess.run(["/bin/launchctl", "print", "system/" + cfg["launchd_label"]], capture_output=True, text=True)
    match = re.search(r"\bpid = (\d+)", response.stdout)
    return response.returncode == 0, int(match.group(1)) if match else None


def verify_process(cfg, pid):
    if pid is None:
        return
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "uid=,command="], capture_output=True, text=True)
    expected = "--app-dir " + cfg["deployment"] + "/app/backend"
    if (result.returncode or not result.stdout.strip().startswith(str(cfg["service_uid"]) + " ")
            or "-m uvicorn recase.api:app" not in result.stdout or expected not in result.stdout):
        raise ValueError("Refusing to change a different running service")


def check_answer(report, expected):
    if report["status"] != "PASS" or report.get("answer_sha256") != expected["sha256"]:
        raise RuntimeError("Real answer denial/hash verification failed")


def check_model(actual, expected):
    fields = ("model", "revision", "config_sha256", "tokenizer_sha256", "quantization", "adapter_sha256", "lora_modules")
    if not actual.get("adapter_loaded") or any(actual.get(key) != expected.get(key) for key in fields):
        raise RuntimeError("The isolated service model/adapter differs from the original verified model")


def apply(cfg):
    if os.geteuid() != 0:
        raise PermissionError("Run --apply with sudo in the user's local terminal")
    os.umask(0o077)
    run, deploy = Path(cfg["run"]), Path(cfg["deployment"])
    app, directory = deploy / "app", deploy / "app/runtime"
    for path in (deploy, app, directory):
        root_path(path, directory=True)
    if {p.name for p in directory.iterdir()} != {"model.lock"}:
        raise ValueError("Refusing to expose unexpected contents of the public lock directory")
    validate_lock_pair(PROJECT / "runtime/model.lock", directory / "model.lock", cfg["operator_uid"], cfg["service_gid"])
    root_path(cfg["launchd_plist"])
    with open(cfg["launchd_plist"], "rb") as stream:
        job = plistlib.load(stream)
    if (job.get("UserName") != SERVICE or job.get("GroupName") != SERVICE
            or job.get("WorkingDirectory") != str(app)
            or job.get("ProgramArguments", []) != [str(deploy / "venv/bin/python"), "-m", "uvicorn", "recase.api:app",
                "--app-dir", str(app / "backend"), "--host", "127.0.0.1", "--port", "8100", "--workers", "1",
                "--no-access-log", "--no-server-header", "--log-level", "warning"]):
        raise ValueError("Launch daemon does not match this deployment")
    loaded, pid = daemon_state(cfg)
    verify_process(cfg, pid)
    listening = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP:8100", "-sTCP:LISTEN", "-t"], capture_output=True, text=True)
    if any(int(value) != pid for value in listening.stdout.split()):
        raise ValueError("Another process owns port8100; no service was stopped")
    out = run / ("finish-" + datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6])
    out.mkdir(mode=0o700)
    os.chown(out, cfg["operator_uid"], cfg["operator_gid"])

    def save(name, data):
        fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.fchown(fd, cfg["operator_uid"], cfg["operator_gid"])
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())

    save("before.json", {"checked_at": now(), "pid": pid, "runtime_mode": oct(stat.S_IMODE(directory.stat().st_mode)), "readiness": readiness()})
    print("[1/3] Repairing only the public model-lock directory (0755).", flush=True)
    os.chmod(directory, 0o755)
    live = readiness()
    try:
        if not live or not live.get("ready") or not live.get("model", {}).get("adapter_loaded"):
            print("[2/3] Restarting the existing isolated service; waiting for model startup...", flush=True)
            if loaded:
                subprocess.run(["/bin/launchctl", "bootout", "system/" + cfg["launchd_label"]], check=True, capture_output=True)
            for _ in range(60):
                if pid is None:
                    break
                old = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
                if old.returncode or old.stdout.strip().startswith("Z"):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Previous process did not stop; a second model was not started")
            subprocess.run(["/bin/launchctl", "bootstrap", "system", cfg["launchd_plist"]], check=True, capture_output=True)
            live = None
            for elapsed in range(120):
                live = readiness()
                if live and live.get("ready") and live.get("model", {}).get("adapter_loaded"):
                    break
                if live and live.get("error"):
                    raise RuntimeError("Service startup failed: " + str(live["error"]))
                if elapsed and elapsed % 10 == 0:
                    print("Model startup still in progress (" + str(elapsed) + "s).", flush=True)
                time.sleep(1)
            else:
                raise RuntimeError("Service startup exceeded120 seconds; rerun this finish command to inspect/resume")
        _, pid = daemon_state(cfg)
        if pid is None:
            raise RuntimeError("No running isolated service PID")
        verify_process(cfg, pid)
        check_model(live["model"], json.loads((run / "final-live-check.json").read_text())["actual_model"])
        print("[3/3] Verifying actual answer-file denials and evaluator hashes...", flush=True)
        sys.path.insert(0, str(PROJECT / "backend"))
        from scripts.verify_os_isolation import verify, probe
        reports = []
        for answer in cfg["volume"]["answer_files"]:
            report = verify(SERVICE, cfg["operator"], answer["protected_copy"], cfg["protected_root"], PROJECT, pid)
            check_answer(report, answer)
            reports.append(report)
            save("isolation-" + Path(answer["protected_copy"]).stem + ".json", report)
        paths = [PROJECT / "data/processed/test.jsonl", Path(cfg["volume"]["key_file"]),
                 run / "prepared/answers/nli_diagnostic.jsonl",
                 PROJECT / "outputs/runs/20261020T132756+0900-review-evaluation-ab725f/answers/nli_diagnostic.jsonl"]
        copies = [{"path": str(path), **probe(SERVICE, path, "open")} for path in paths]
        if any(not p.get("probe_executed") or p.get("opened") or p.get("errno") not in (1, 13) for p in copies):
            raise RuntimeError("Workspace answer/key copy denial failed")
        result = {"status": "PASS", "checked_at": now(), "service_user": SERVICE, "service_uid": cfg["service_uid"],
                  "service_pid": pid, "evaluator_user": cfg["operator"], "evaluator_uid": cfg["operator_uid"],
                  "deployment": str(deploy), "launchd_label": cfg["launchd_label"], "service_ready": True,
                  "actual_model": live["model"], "answers": reports, "workspace_answer_and_key_denial": copies,
                  "shared_model_lock_inode": (directory / "model.lock").stat().st_ino,
                  "human_reviewed": False, "new_training_runs": 0, "output": str(out),
                  "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        save("result.json", result)
        print(json.dumps({key: result[key] for key in ("status", "service_uid", "service_pid", "output")}), flush=True)
        return result
    except (Exception, KeyboardInterrupt) as error:
        save("incomplete.json", {"status": "INCOMPLETE", "checked_at": now(), "error": type(error).__name__,
                                 "message": str(error), "safe_to_rerun_finish_command": True,
                                 "human_reviewed": False, "new_training_runs": 0})
        print("Incomplete. Existing account/data were retained. Evidence: " + str(out), flush=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    cfg = plan(args.run)
    if args.apply:
        apply(cfg)
    else:
        print(json.dumps({key: cfg[key] for key in ("run", "deployment", "service_uid", "operator_uid", "launchd_label")}, indent=2))


if __name__ == "__main__":
    main()
