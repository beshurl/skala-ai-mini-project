"""Probe a REAL answer file under two real UIDs. Does not create users/volumes.

Run from the evaluator account or an administrator with noninteractive sudo
authorization. An EACCES from sudo itself is BLOCKED, never evidence of file denial.
"""
import argparse
import errno
import json
import os
import pwd
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import file_digest, utc_now
from recase.paths import PROJECT_ROOT
from scripts.dataset_control import write_new

PROBE = """
import errno, hashlib, json, os, sys
result = {'uid': os.getuid(), 'euid': os.geteuid(), 'opened': False}
try:
    h = hashlib.sha256()
    with open(sys.argv[1], 'rb') as f:
        result['device'] = os.fstat(f.fileno()).st_dev
        result['inode'] = os.fstat(f.fileno()).st_ino
        if sys.argv[2] == 'hash':
            for block in iter(lambda: f.read(1048576), b''): h.update(block)
            result['sha256'] = h.hexdigest()
        else: f.read(1)
    result['opened'] = True
except OSError as e:
    result['errno'] = e.errno
print(json.dumps(result))
"""


def probe(user, answers, mode):
    account = pwd.getpwnam(user)
    command = [os.path.realpath(sys.executable), "-I", "-c", PROBE, str(answers), mode]
    if os.geteuid() != account.pw_uid:
        command = ["/usr/bin/sudo", "-n", "-u", user, "--", *command]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    if result.returncode:
        return {"probe_executed": False, "process_exit_code": result.returncode,
                "reason": "ACCOUNT_SWITCH_OR_INTERPRETER_UNAVAILABLE"}
    try:
        report = json.loads(result.stdout)
    except ValueError:
        return {"probe_executed": False, "reason": "INVALID_PROBE_OUTPUT"}
    report["probe_executed"] = report.get("uid") == account.pw_uid and report.get("euid") == account.pw_uid
    return report


def verify(service_user, evaluator_user, answers, protected_root, workspace, service_pid=None):
    answers, root, workspace = (Path(p).resolve(strict=True) for p in (answers, protected_root, workspace))
    if not answers.is_file() or not root.is_dir() or not answers.is_relative_to(root):
        raise ValueError("Existing answer file within protected root required")
    service, evaluator = pwd.getpwnam(service_user), pwd.getpwnam(evaluator_user)
    service_probe = probe(service_user, answers, "open")
    evaluator_probe = probe(evaluator_user, answers, "hash")
    checks = {"different_nonroot_uids": service.pw_uid != evaluator.pw_uid and service.pw_uid > 0 and evaluator.pw_uid > 0,
              "separate_volume": root.stat().st_dev != workspace.stat().st_dev,
              "protected_root_owner": root.stat().st_uid == evaluator.pw_uid,
              "protected_root_mode": root.stat().st_mode & 0o077 == 0,
              "answer_owner": answers.stat().st_uid == evaluator.pw_uid,
              "answer_mode": answers.stat().st_mode & 0o077 == 0,
              "evaluator_reads_real_answers": evaluator_probe.get("probe_executed") is True and evaluator_probe.get("opened") is True,
              "service_denied_real_answers": service_probe.get("probe_executed") is True and service_probe.get("opened") is False
                  and service_probe.get("errno") in (errno.EACCES, errno.EPERM)}
    if service_pid:
        result = subprocess.run(["/bin/ps", "-p", str(service_pid), "-o", "uid="], capture_output=True, text=True)
        checks["running_service_uid_matches"] = result.returncode == 0 and result.stdout.strip() == str(service.pw_uid)
    return {"kind": "real_answer_os_isolation", "checked_at": utc_now(),
            "status": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks,
            "service_user": service_user, "service_uid": service.pw_uid,
            "evaluator_user": evaluator_user, "evaluator_uid": evaluator.pw_uid,
            "answers": str(answers), "protected_root": str(root),
            "answer_sha256": evaluator_probe.get("sha256"),
            "service_probe": service_probe, "evaluator_probe": evaluator_probe,
            "verifier_sha256": file_digest(__file__),
            "limitations": ["Checks this file/path at this time; copies, backups and privileged administrators require separate controls.",
                            "A noninteractive account-switch failure does not demonstrate access denial."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("service-user", "evaluator-user", "answers", "protected-root", "out"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--workspace", default=str(PROJECT_ROOT))
    parser.add_argument("--service-pid", type=int)
    args = parser.parse_args()
    report = verify(args.service_user, args.evaluator_user, args.answers, args.protected_root, args.workspace, args.service_pid)
    write_new(args.out, report)
    print(json.dumps({"status": report["status"], "checks": report["checks"], "out": args.out}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
