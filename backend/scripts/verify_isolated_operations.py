"""Plan/apply a backup and scratch recovery drill under the existing service UID.

Apply needs administrator authentication in the user's terminal to switch UID.
It never stops the service, changes accounts/permissions, or deletes live cases.
Only metadata is returned; backup contents remain in private service storage.
"""
import argparse
import hashlib
import json
import os
import pwd
import stat
import signal
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import digest, file_digest, utc_now
from recase.paths import BACKEND_ROOT, PROJECT_ROOT
from scripts.dataset_control import write_new
from scripts.finish_local_isolation import plan as deployment_plan, root_path, readiness, verify_process

MODULES = ("__init__.py", "store.py", "ledger.py", "retention.py", "lifecycle.py")
WORKER = BACKEND_ROOT / "recase/operations_drill.py"
POLICY = PROJECT_ROOT / "data/local_operations_policy.json"


def public_sources(deploy):
    root_path(deploy, directory=True)
    backend = deploy / "app/backend"
    for folder in (deploy / "app", backend, backend / "recase"):
        root_path(folder, directory=True)
    hashes = {}
    for name in MODULES:
        path = backend / "recase" / name
        info = path.lstat()
        # clonefile preserved the evaluator's ownership on these public files.
        # Root-owned directories + 0644 operator/root files deny service writes;
        # do not claim protection from the evaluator who owns the source project.
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, PROJECT_ROOT.stat().st_uid)
                or stat.S_IMODE(info.st_mode) != 0o644):
            raise ValueError("Expected regular operator/root public modules read-only to the service")
        actual = file_digest(path)
        if actual != file_digest(BACKEND_ROOT / "recase" / name):
            raise ValueError("Deployed operations modules differ; review deployment drift first")
        hashes[name] = actual
    return hashes


def policy_identity():
    value = json.loads(POLICY.read_text())
    if (value.get("scope") != "personal_loopback_synthetic_service_only"
            or value.get("automatic_case_deletion") is not False
            or value.get("automatic_backup_disposal") is not False):
        raise ValueError("Only the current manual synthetic policy belongs in this drill")
    return {"path": str(POLICY), "sha256": file_digest(POLICY), "version": value["version"]}


def build_plan(isolation_run, result_directory):
    cfg = deployment_plan(isolation_run)
    deploy = Path(cfg["deployment"])
    if os.geteuid() not in (0, cfg["operator_uid"]):
        raise PermissionError("Use the recorded evaluator account")
    result = Path(result_directory).absolute()
    if result.is_symlink() or any(p.is_symlink() for p in result.parents):
        raise ValueError("Regular result directory required")
    if not result.resolve().is_relative_to(PROJECT_ROOT / "outputs/runs") or result.stat().st_uid != cfg["operator_uid"] or result.stat().st_mode & 0o077:
        raise PermissionError("Private operator-owned result directory under outputs/runs required")
    reports = sorted(Path(isolation_run).glob("finish-*/result.json"))
    proofs = [json.loads(p.read_text()) for p in reports]
    proofs = [p for p in proofs if p.get("status") == "PASS" and p.get("service_uid") == cfg["service_uid"]]
    if not proofs:
        raise ValueError("A passed actual isolated-service result is required")
    proof = proofs[-1]
    verify_process(cfg, proof["service_pid"])
    live = readiness()
    if not live or not live.get("ready"):
        raise ValueError("The current isolated service must be ready before planning")
    nonce = uuid.uuid4().hex
    plan = {"version": "isolated-operations-v1", "created_at": utc_now(), "isolation_run": str(Path(isolation_run).resolve()),
            "deployment": str(deploy), "service_user": cfg["service"], "service_uid": cfg["service_uid"],
            "service_pid": proof["service_pid"], "operator_uid": cfg["operator_uid"], "operator_gid": cfg["operator_gid"],
            "backend": str(deploy / "app/backend"), "source_db": str(deploy / "state/recase.sqlite3"),
            "source_journal": str(deploy / "state/deletions.jsonl"),
            "scratch": str(deploy / "state" / ("operations-check-" + nonce)),
            "receipt_directory": str(result / ("execution-" + nonce)),
            "helper_sha256": file_digest(__file__), "worker_sha256": file_digest(WORKER),
            "operations_policy": policy_identity(),
            "public_code_owner_scope": "Root-owned directories, operator/root-owned mode0644 files; read-only to the service, not a boundary against the evaluator",
            "deployed_module_hashes": public_sources(deploy), "model_calls": 0, "trains_model": False,
            "live_service_changes": [], "production_deletion": False,
            "planned_actions": ["Use the actual nonroot service UID and its deployed SQLite/retention modules",
                                "Take a consistent mode=ro live SQLite backup into a new private service directory",
                                "Copy the latest independent journal without modifying it",
                                "Create/delete a new synthetic target only in scratch copies, restore and replay tombstones",
                                "Check sessions, evidence/jobs/events, survivor, hashes, mode0600 and integrity",
                                "Return metadata only; leave the service, original backup and production journal in place"]}
    plan["plan_sha256"] = digest(plan)
    return plan


def checked_plan(path):
    path = Path(path).absolute()
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or any(p.is_symlink() for p in path.parents)):
        raise PermissionError("Private regular plan file required")
    data = json.loads(path.read_text())
    if data.get("plan_sha256") != digest({k: v for k, v in data.items() if k != "plan_sha256"}):
        raise ValueError("Operations plan changed")
    if info.st_uid != data["operator_uid"] or data["version"] != "isolated-operations-v1":
        raise ValueError("Plan operator/version mismatch")
    return data


def apply(plan_path):
    if os.geteuid() != 0:
        raise PermissionError("Run --apply with sudo in the user's local terminal; no password in arguments")
    data = checked_plan(plan_path)
    cfg = deployment_plan(data["isolation_run"])
    deploy = Path(cfg["deployment"])
    account = pwd.getpwnam(cfg["service"])
    expected = {"deployment": str(deploy), "service_user": cfg["service"], "service_uid": account.pw_uid,
                "operator_uid": cfg["operator_uid"], "operator_gid": cfg["operator_gid"],
                "backend": str(deploy / "app/backend"), "source_db": str(deploy / "state/recase.sqlite3"),
                "source_journal": str(deploy / "state/deletions.jsonl"),
                "helper_sha256": file_digest(__file__), "worker_sha256": file_digest(WORKER),
                "operations_policy": policy_identity(),
                "deployed_module_hashes": public_sources(deploy)}
    if any(data.get(k) != v for k, v in expected.items()):
        raise ValueError("Account, input paths or reviewed operations source changed")
    if data.get("production_deletion") is not False or data.get("live_service_changes") != []:
        raise ValueError("Only a read-only production snapshot and copy-only drill is allowed")
    scratch, receipt = Path(data["scratch"]), Path(data["receipt_directory"])
    if (scratch.parent != deploy / "state" or not scratch.name.startswith("operations-check-")
            or receipt.parent != Path(plan_path).absolute().parent or not receipt.name.startswith("execution-")):
        raise ValueError("Unexpected scratch or receipt path")
    root_path(deploy / "app/runtime", directory=True)
    state = (deploy / "state").lstat()
    if not stat.S_ISDIR(state.st_mode) or state.st_uid != account.pw_uid or stat.S_IMODE(state.st_mode) != 0o700:
        raise ValueError("Existing private service state directory required")
    verify_process(cfg, data["service_pid"])
    before = readiness()
    if not before or not before.get("ready") or scratch.exists() or receipt.exists():
        raise ValueError("Ready service and new scratch/receipt paths required; preserve earlier attempts")
    os.umask(0o077)
    receipt.mkdir(mode=0o700)
    os.chown(receipt, cfg["operator_uid"], cfg["operator_gid"])
    def save(name, value):
        write_new(receipt / name, value)
        os.chown(receipt / name, cfg["operator_uid"], cfg["operator_gid"])
    args = [data["backend"], data["source_db"], data["source_journal"], data["scratch"], str(data["service_uid"])]
    source = WORKER.read_text()
    if hashlib.sha256(source.encode()).hexdigest() != data["worker_sha256"]:
        raise ValueError("Worker source changed after plan verification")
    code = source + '\nprint(json.dumps(run(*sys.argv[1:5], int(sys.argv[5])), ensure_ascii=False))\n'
    command = ["/usr/bin/sudo", "-n", "-u", cfg["service"], "--", str(deploy / "venv/bin/python"), "-I", "-c", code, *args]
    started = utc_now()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=deploy, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=180)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        # Stop only the fresh process group created for this scratch drill.
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        save("incomplete.json", {"started_at": started, "finished_at": utc_now(), "status": "INCOMPLETE",
             "error": type(error).__name__, "worker_sha256": data["worker_sha256"],
             "service_stopped": False, "production_deletion_calls": 0, "scratch": data["scratch"]})
        raise
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    save("execution.json", {"started_at": started, "finished_at": utc_now(), "exit_code": result.returncode,
         "worker_source": str(WORKER), "worker_sha256": data["worker_sha256"], "worker_arguments": args,
         "interpreter": str(deploy / "venv/bin/python"), "sudo_target": cfg["service"],
         "plan_sha256": data["plan_sha256"], "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError("Service-account operations worker failed; preserve the new receipt and scratch directory")
    report = json.loads(result.stdout)
    if (report.get("status") != "PASS" or report.get("worker_uid") != account.pw_uid
            or report.get("worker_euid") != account.pw_uid or report.get("model_calls") != 0
            or report.get("production_delete_calls") != 0):
        raise RuntimeError("Actual service UID and operations invariants did not pass")
    expected_modules = {"recase." + name.removesuffix(".py"): value
                        for name, value in data["deployed_module_hashes"].items() if name != "__init__.py"}
    if report.get("executed_module_hashes") != expected_modules:
        raise RuntimeError("Executed service modules differ from the reviewed plan")
    verify_process(cfg, data["service_pid"])
    after = readiness()
    if not after or not after.get("ready") or after["model"] != before["model"]:
        raise RuntimeError("Service/model changed during the drill; preserve the receipt")
    report.update(service_pid=data["service_pid"], service_ready_before=True, service_ready_after=True,
                  isolated_service_validated=True, completed_at=utc_now(), plan_sha256=data["plan_sha256"])
    save("result.json", report)
    print(json.dumps({"status": "PASS", "service_uid": account.pw_uid, "result": str(receipt / "result.json")}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--isolation-run")
    p.add_argument("--out", help="New plan file in a private existing outputs/runs directory")
    p.add_argument("--plan", help="Previously inspected hash-bound operations plan")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if a.apply:
        if not a.plan or a.out or a.isolation_run:
            p.error("Apply requires only --plan and --apply")
        return apply(a.plan)
    if a.plan:
        print(json.dumps(checked_plan(a.plan), ensure_ascii=False, indent=2))
        return
    if not a.isolation_run or not a.out:
        p.error("Planning requires --isolation-run and --out")
    value = build_plan(a.isolation_run, Path(a.out).parent)
    write_new(a.out, value)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
