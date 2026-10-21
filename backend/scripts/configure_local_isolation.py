"""Prepare/apply one isolated local service deployment. Root is required to apply.

Creates only a new disabled-login service account and a new deployment. Existing
accounts are never edited. The operator remains the evaluator. Actual account
and answer-file checks are mandatory; no human-review approval is created.
"""
import argparse
import base64
import ctypes
import grp
import hashlib
import json
import os
import plistlib
import pwd
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SERVICE = "_recase_service"
REVISION = "4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25"


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def checked(command, **kwargs):
    result = subprocess.run(command, capture_output=True, timeout=60, **kwargs)
    if result.returncode:
        # No credentials are ever passed in argv. Keep diagnostics out of stdout.
        raise RuntimeError("COMMAND_FAILED " + command[0] + " exit=" + str(result.returncode))
    return result.stdout


def plan(run, service_pid):
    run = Path(run).resolve(strict=True)
    if not run.is_relative_to(PROJECT / "outputs/runs") or not (run / "protected_volume.json").is_file():
        raise ValueError("An existing volume-preparation run under outputs/runs is required")
    volume = json.loads((run / "protected_volume.json").read_text())
    operator_uid = Path(volume["protected_root"]).stat().st_uid
    operator = pwd.getpwuid(operator_uid)
    if operator_uid == 0:
        raise ValueError("Nonroot evaluator required")
    try:
        pwd.getpwnam(SERVICE)
        raise ValueError("Service account already exists; refusing to change it")
    except KeyError:
        pass
    try:
        grp.getgrnam(SERVICE)
        raise ValueError("Service group already exists; refusing to change it")
    except KeyError:
        pass
    used_uids = {p.pw_uid for p in pwd.getpwall()}
    used_gids = {g.gr_gid for g in grp.getgrall()}
    role_id = next(i for i in range(499, 449, -1) if i not in used_uids and i not in used_gids)
    deploy = Path("/Users/Shared") / ("RECASE-isolated-" + run.name.rsplit("-", 1)[-1])
    if deploy.exists():
        raise FileExistsError("New deployment path required")
    process = checked(["/bin/ps", "-p", str(service_pid), "-o", "uid=,command="], text=True).strip()
    if not process.startswith(str(operator_uid) + " ") or "-m uvicorn recase.api:app" not in process or "--port 8100" not in process:
        raise ValueError("Expected operator-owned RE:CASE server on port8100")
    cwd = checked(["/usr/sbin/lsof", "-a", "-p", str(service_pid), "-d", "cwd", "-Fn"], text=True)
    if "n" + str(PROJECT) not in cwd.splitlines():
        raise ValueError("Existing server is not running in this project")
    protected = Path(volume["protected_root"]).resolve(strict=True)
    if protected.stat().st_dev == PROJECT.stat().st_dev or protected.stat().st_mode & 0o077:
        raise ValueError("Separate protected volume with mode0700 required")
    if not volume.get("owners_enabled") or not volume.get("image_encryption", {}).get("encrypted"):
        raise ValueError("Ownership enforcement and encrypted disk image required")
    return {"run": str(run), "operator": operator.pw_name, "operator_uid": operator_uid,
            "operator_gid": operator.pw_gid, "service": SERVICE, "service_uid": role_id, "service_gid": role_id,
            "deployment": str(deploy), "existing_service_pid": service_pid,
            "protected_root": str(protected), "volume": volume,
            "changes": ["Create a dedicated nonadmin disabled-login service account/group",
                        "Copy only app, cached model/runtime, adapter and synthetic service state to a new deployment",
                        "Keep the original and deployed model locks on the same inode",
                        "Switch only the verified existing port8100 service after preparation",
                        "Probe real answers from evaluator/service UIDs and verify the running service UID"],
            "creates_human_review": False, "trains_model": False}


def clone_copy(source, target):
    source, target = os.fspath(source), os.fspath(target)
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    clone = library.clonefile
    clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clone.restype = ctypes.c_int
    if clone(os.fsencode(source), os.fsencode(target), 0) != 0:
        shutil.copy2(source, target)
    return target


def create_model_runtime(path):
    """The public lock directory must remain traversable under a private umask."""
    path.mkdir(mode=0o755)
    os.chmod(path, 0o755)


def apply(configuration):
    if os.geteuid() != 0:
        raise PermissionError("macOS administrator authentication is required; do not put a password in this command")
    cfg = configuration
    run, deploy = Path(cfg["run"]), Path(cfg["deployment"])
    uid, gid = cfg["service_uid"], cfg["service_gid"]
    original_pid = cfg["existing_service_pid"]
    label = "com.recase.isolated." + deploy.name.rsplit("-", 1)[-1]
    plist_path = Path("/Library/LaunchDaemons") / (label + ".plist")
    if plist_path.exists():
        raise FileExistsError("Refusing an existing launch daemon")
    os.umask(0o077)
    progress = run / "admin-progress.jsonl"
    def event(phase, **fields):
        print(json.dumps({"phase": phase, **fields}), flush=True)
        fd = os.open(progress, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        os.fchown(fd, cfg["operator_uid"], cfg["operator_gid"])
        with os.fdopen(fd, "a") as stream:
            stream.write(json.dumps({"phase": phase, "time": time.time(), **fields}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    def user_command(command):
        return checked(["/usr/bin/sudo", "-n", "-u", SERVICE, "--", *command], text=True, cwd=deploy)
    def private_tree(path):
        for directory, dirs, files in os.walk(path):
            os.chown(directory, uid, gid)
            os.chmod(directory, 0o700)
            for filename in files:
                item = Path(directory) / filename
                if not item.is_symlink():
                    os.chown(item, uid, gid)
                    os.chmod(item, 0o600)

    event("preparation_started")
    deploy.mkdir(mode=0o755)
    home = deploy / "home"
    home.mkdir(mode=0o700)
    user_record, group_record = "/Users/" + SERVICE, "/Groups/" + SERVICE
    for record, attributes in ((group_record, {"PrimaryGroupID": str(gid), "Password": "*", "GroupMembership": SERVICE}),
                               (user_record, {"UniqueID": str(uid), "PrimaryGroupID": str(gid), "NFSHomeDirectory": str(home),
                                              "UserShell": "/usr/bin/false", "RealName": "RECASE isolated local service",
                                              "Password": "*", "AuthenticationAuthority": ";DisabledUser;", "IsHidden": "1"})):
        checked(["/usr/bin/dscl", ".", "-create", record])
        for key, value in attributes.items():
            checked(["/usr/bin/dscl", ".", "-create", record, key, value])
    os.chown(home, uid, gid)
    account = pwd.getpwnam(SERVICE)
    if account.pw_uid != uid or "admin" in user_command(["/usr/bin/id", "-Gn"]).split():
        raise RuntimeError("Service identity/nonadmin verification failed")
    event("nonadmin_service_account_created", uid=uid, gid=gid)
    app = deploy / "app"
    (app / "backend").mkdir(parents=True, mode=0o755)
    shutil.copytree(PROJECT / "backend/recase", app / "backend/recase", copy_function=clone_copy,
                    ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    (app / "frontend").mkdir(mode=0o755)
    for part in ("dist", "public"):
        shutil.copytree(PROJECT / "frontend" / part, app / "frontend" / part, copy_function=clone_copy)
    shutil.copytree(PROJECT / ".venv", deploy / "venv", symlinks=True, copy_function=clone_copy,
                    ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    model_source = Path(pwd.getpwuid(cfg["operator_uid"]).pw_dir) / ".cache/huggingface/hub/models--mlx-community--Qwen3-4B-4bit/snapshots" / REVISION
    model_repo = app / "model-cache/models--mlx-community--Qwen3-4B-4bit"
    model_snapshot = model_repo / "snapshots" / REVISION
    model_snapshot.mkdir(parents=True, mode=0o755)
    for path in model_source.iterdir():
        if path.is_file():
            clone_copy(path.resolve(), model_snapshot / path.name)
    (model_repo / "refs").mkdir(mode=0o755)
    (model_repo / "refs/main").write_text(REVISION)
    (app / "outputs").mkdir(mode=0o755)
    shutil.copytree(PROJECT / "outputs/mlx_adapter", app / "outputs/mlx_adapter", copy_function=clone_copy)
    # Public code/model/runtime is root-owned and not writable by the service.
    for directory, dirs, files in os.walk(deploy):
        if Path(directory).is_relative_to(home):
            continue
        os.chmod(directory, 0o755)
        for filename in files:
            path = Path(directory) / filename
            if not path.is_symlink():
                executable = bool(path.stat().st_mode & 0o111)
                os.chmod(path, 0o755 if executable else 0o644)
    (deploy / "logs").mkdir(mode=0o700)
    (deploy / "secrets").mkdir(mode=0o700)
    model_runtime = app / "runtime"
    create_model_runtime(model_runtime)
    runtime = deploy / "state"
    runtime.mkdir(mode=0o700)
    for folder in (home, deploy / "logs", deploy / "secrets", runtime):
        os.chown(folder, uid, gid)
    lock = PROJECT / "runtime/model.lock"
    if not lock.is_file() or lock.is_symlink():
        raise ValueError("Expected the real existing model lock")
    os.chown(lock, cfg["operator_uid"], gid)
    os.chmod(lock, 0o660)
    os.link(lock, model_runtime / "model.lock")
    interpreter = deploy / "venv/bin/python"
    metal = json.loads(user_command([str(interpreter), "-I", "-c",
        "import json,os,mlx.core as mx; print(json.dumps({'uid':os.getuid(),'metal':mx.metal.is_available()}))"]))
    if metal != {"uid": uid, "metal": True}:
        raise RuntimeError("Service interpreter/Metal initialization failed")
    event("deployment_prepared", metal_available=True, model_weights_loaded=False)
    # No model weights have been loaded in the new UID while the old model runs.
    auth_source = PROJECT / "runtime/personal-auth"
    auth = json.loads((auth_source / "auth.json").read_text())
    token = (auth_source / "key.txt").read_text().strip()
    authorization = "Basic " + base64.b64encode((auth["user"] + ":" + token).encode()).decode()
    def ready():
        try:
            request = urllib.request.Request("http://127.0.0.1:8100/ready", headers={"Authorization": authorization})
            with urllib.request.urlopen(request, timeout=2) as response:
                return json.load(response)
        except (OSError, ValueError):
            return None
    # Recheck the exact PID immediately before stopping only that service.
    check = checked(["/bin/ps", "-p", str(original_pid), "-o", "uid=,command="], text=True).strip()
    if not check.startswith(str(cfg["operator_uid"]) + " ") or "-m uvicorn recase.api:app" not in check:
        raise RuntimeError("Existing service identity changed; cutover refused")
    with sqlite3.connect("file:" + str(PROJECT / "runtime/recase.sqlite3") + "?mode=ro", uri=True) as db:
        if db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[0]:
            raise RuntimeError("Active analysis jobs exist; cutover refused before stopping the service")
    event("cutover_stopping_verified_original_service", pid=original_pid)
    cfg["cutover_started"] = True
    os.kill(original_pid, signal.SIGTERM)
    for _ in range(60):
        state = subprocess.run(["/bin/ps", "-p", str(original_pid), "-o", "stat="], capture_output=True, text=True)
        if state.returncode or state.stdout.strip().startswith("Z"):
            break
        time.sleep(1)
    else:
        raise RuntimeError("Original service did not stop; no second model was started")
    source = sqlite3.connect("file:" + str(PROJECT / "runtime/recase.sqlite3") + "?mode=ro", uri=True)
    target = sqlite3.connect(runtime / "recase.sqlite3")
    source.backup(target)
    target.close()
    source.close()
    shutil.copyfile(PROJECT / "runtime/deletions.jsonl", runtime / "deletions.jsonl")
    shutil.copyfile(auth_source / "auth.json", deploy / "secrets/auth.json")
    for folder in (runtime, deploy / "secrets"):
        # The shared lock inode remains operator-owned, group-accessible.
        for path in folder.iterdir():
            if path.name != "model.lock":
                os.chown(path, uid, gid)
                os.chmod(path, 0o600)
    environment = {"HOME": str(home), "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                   "PYTHONPATH": str(app / "backend"), "HF_HUB_CACHE": str(app / "model-cache"), "HF_HUB_OFFLINE": "1",
                   "RECASE_MODE": "personal", "RECASE_DB": str(runtime / "recase.sqlite3"),
                   "RECASE_AUTH_FILE": str(deploy / "secrets/auth.json"), "RECASE_DELETIONS": str(runtime / "deletions.jsonl"),
                   "RECASE_ADAPTER": str(app / "outputs/mlx_adapter"), "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
                   "DO_NOT_TRACK": "1"}
    job = {"Label": label, "UserName": SERVICE, "GroupName": SERVICE, "RunAtLoad": True,
           "ProgramArguments": [str(interpreter), "-m", "uvicorn", "recase.api:app", "--app-dir", str(app / "backend"),
                                "--host", "127.0.0.1", "--port", "8100", "--workers", "1", "--no-access-log", "--no-server-header", "--log-level", "warning"],
           "WorkingDirectory": str(app), "EnvironmentVariables": environment,
           "StandardOutPath": str(deploy / "logs/service.log"), "StandardErrorPath": str(deploy / "logs/service-error.log")}
    fd = os.open(plist_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream:
        plistlib.dump(job, stream)
    launched = False
    try:
        checked(["/bin/launchctl", "bootstrap", "system", str(plist_path)])
        launched = True
        event("isolated_service_bootstrapped", label=label)
        live = None
        for _ in range(60):
            live = ready()
            if live and live.get("ready") and live.get("model", {}).get("adapter_loaded"):
                break
            time.sleep(1)
        if not live or not live.get("ready"):
            raise RuntimeError("Isolated service did not become ready")
        dump = checked(["/bin/launchctl", "print", "system/" + label], text=True)
        import re
        service_pid = int(re.search(r"\bpid = (\d+)", dump).group(1))
        sys.path.insert(0, str(PROJECT / "backend"))
        from scripts.verify_os_isolation import verify, probe
        reports = []
        for answer in cfg["volume"]["answer_files"]:
            report = verify(SERVICE, cfg["operator"], answer["protected_copy"], cfg["protected_root"], PROJECT, service_pid)
            if report["status"] != "PASS":
                raise RuntimeError("Actual answer isolation check failed")
            reports.append(report)
        workspace_probes = [{"path": str(path), **probe(SERVICE, path, "open")} for path in (
            PROJECT / "data/processed/test.jsonl", Path(cfg["volume"]["key_file"]),
            PROJECT / "outputs/runs/20261020T132756+0900-review-evaluation-ab725f/answers/nli_diagnostic.jsonl")]
        if any(not p.get("probe_executed") or p.get("opened") or p.get("errno") not in (1, 13) for p in workspace_probes):
            raise RuntimeError("Service can reach a workspace answer/key copy")
        result = {"status": "PASS", "service_user": SERVICE, "service_uid": uid, "service_pid": service_pid,
                  "evaluator_user": cfg["operator"], "evaluator_uid": cfg["operator_uid"],
                  "deployment": str(deploy), "launchd_label": label, "launchd_plist": str(plist_path),
                  "service_ready": True, "actual_model": live["model"], "answers": reports,
                  "workspace_answer_and_key_denial": workspace_probes,
                  "shared_model_lock_inode": lock.stat().st_ino, "human_reviewed": False, "new_training_runs": 0}
        fd = os.open(run / "applied-isolation.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.fchown(fd, cfg["operator_uid"], cfg["operator_gid"])
        with os.fdopen(fd, "w") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        event("all_actual_answer_denials_verified", answer_files=len(reports), service_uid=uid)
        return result
    except (Exception, KeyboardInterrupt):
        if launched:
            subprocess.run(["/bin/launchctl", "bootout", "system/" + label], capture_output=True)
        # Preserve synthetic data accepted during a failed new service attempt.
        event("isolated_activation_failed_original_service_restore_required")
        raise


def restore_original(cfg):
    """Recover only a cutover this invocation actually started, without a new model overlap."""
    if not cfg.get("cutover_started"):
        return
    for _ in range(15):
        listening = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP:8100", "-sTCP:LISTEN", "-t"], capture_output=True, text=True)
        if not listening.stdout.strip():
            break
        time.sleep(1)
    else:
        return  # Do not kill or replace another server that acquired the port.
    log = open(Path(cfg["run"]) / "original-service-restore.log", "ab", buffering=0)
    subprocess.Popen(["/usr/bin/sudo", "-n", "-u", cfg["operator"], "--", "/usr/bin/env",
                      "RECASE_MODE=personal", "RECASE_AUTH_FILE=" + str(PROJECT / "runtime/personal-auth/auth.json"),
                      "RECASE_DELETIONS=" + str(PROJECT / "runtime/deletions.jsonl"), "PYTHONPATH=" + str(PROJECT / "backend"),
                      str(PROJECT / ".venv/bin/python"), "-m", "uvicorn", "recase.api:app", "--app-dir", str(PROJECT / "backend"),
                      "--host", "127.0.0.1", "--port", "8100", "--workers", "1", "--no-access-log", "--no-server-header", "--log-level", "warning"],
                     cwd=PROJECT, stdout=log, stderr=log, start_new_session=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--service-pid", required=True, type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    configuration = plan(args.run, args.service_pid)
    if args.apply:
        try:
            result = apply(configuration)
        except (Exception, KeyboardInterrupt):
            restore_original(configuration)
            raise
        print(json.dumps({key: result[key] for key in ("status", "service_user", "service_uid", "service_pid", "service_ready")}, ensure_ascii=False))
    else:
        print(json.dumps(configuration, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
