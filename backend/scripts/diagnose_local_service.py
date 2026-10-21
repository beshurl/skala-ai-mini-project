"""Read-only UID499 diagnostics. Run with sudo in the user's local terminal.

Reports only allowlisted metadata and aggregate job states. Does not repair,
chmod, restart, submit jobs, load models, or use immutable SQLite snapshots.
"""
import argparse
import json
import os
import plistlib
import pwd
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LABEL = "com.recase.isolated.0385fc"
SERVICE = "_recase_service"
DEPLOY = Path("/Users/Shared/RECASE-isolated-0385fc")
DATABASE = DEPLOY / "state/recase.sqlite3"
PLIST = Path("/Library/LaunchDaemons") / (LABEL + ".plist")

# Passed as code to an isolated interpreter after dropping to the service UID.
# The service cannot read the operator's source directory; no permission change
# or source-file copying is needed. Never print database strings or credentials.
PROBE = r'''
import json,os,sqlite3,stat,sys,time
from pathlib import Path
from contextlib import closing
path=Path(sys.argv[1])
report={'uid':os.getuid(),'euid':os.geteuid(),'sqlite_version':sqlite3.sqlite_version,'metadata':{},'database_opened':False,'job_state':'UNKNOWN'}
for item in [path.parent,path,Path(str(path)+'-wal'),Path(str(path)+'-shm')]:
 row={}
 try:
  info=item.lstat()
  row={'exists':True,'uid':info.st_uid,'gid':info.st_gid,'mode':oct(stat.S_IMODE(info.st_mode)),'device':info.st_dev,'inode':info.st_ino,'bytes':info.st_size,'symlink':stat.S_ISLNK(info.st_mode),'regular':stat.S_ISREG(info.st_mode),'readable':os.access(item,os.R_OK),'writable':os.access(item,os.W_OK)}
 except OSError as exc:row={'exists':False if exc.errno==2 else None,'errno':exc.errno}
 report['metadata'][item.name]=row
source=report['metadata'][path.name]
try:
 if source.get('exists') is not True or not source.get('regular') or source.get('symlink'):
  report['classification']='DATABASE_MISSING_OR_UNSAFE'
 elif not source.get('readable'):
  report['classification']='DATABASE_NOT_READABLE_AS_SERVICE'
 else:
  # mode=ro retains live WAL visibility; immutable=1 could hide current jobs.
  with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
   db.execute('PRAGMA query_only=ON')
   report['database_opened']=True
   allowed={'QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED','CANCELLED'}
   counts={}
   for state,count in db.execute('SELECT status,count(*) FROM jobs GROUP BY status'):
    key=state if state in allowed else 'UNRECOGNIZED_STATUS'
    counts[key]=counts.get(key,0)+count
   report['job_counts']=counts
   report['active_jobs']=counts.get('QUEUED',0)+counts.get('RUNNING',0)
   report['active_samples']=[{'status':state,'cancel_requested':bool(cancel),'age_seconds':max(0,int(time.time()-created))} for state,cancel,created in db.execute("SELECT status,cancel_requested,created FROM jobs WHERE status IN ('QUEUED','RUNNING') ORDER BY created LIMIT 10")]
   report['job_state']='ACTIVE' if report['active_jobs'] else 'IDLE_AT_QUERY_TIME'
   report['classification']='READ_ONLY_QUERY_SUCCEEDED'
except (OSError,sqlite3.Error,TypeError,ValueError) as exc:
 report['classification']='READ_ONLY_QUERY_FAILED'
 report['error']={'type':type(exc).__name__,'errno':getattr(exc,'errno',None),'sqlite_errorcode':getattr(exc,'sqlite_errorcode',None),'sqlite_errorname':getattr(exc,'sqlite_errorname',None)}
print(json.dumps(report,sort_keys=True))
'''


def validate_identity(expected_pid):
    account = pwd.getpwnam(SERVICE)
    if account.pw_uid != 499 or expected_pid <= 1:
        raise ValueError("SERVICE_IDENTITY_CHANGED")
    info = PLIST.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError("PROTECTED_PLIST_METADATA_CHANGED")
    with PLIST.open("rb") as stream:
        configuration = plistlib.load(stream)
    if (configuration.get("Label") != LABEL or configuration.get("UserName") != SERVICE
            or configuration.get("EnvironmentVariables", {}).get("RECASE_DB") != str(DATABASE)):
        raise ValueError("CONFIGURED_SERVICE_OR_DATABASE_DIFFERS")
    result = subprocess.run(["/bin/launchctl", "print", "system/" + LABEL], capture_output=True, text=True, timeout=10)
    match = re.search(r"^\s*pid = (\d+)\s*$", result.stdout, re.M)
    if result.returncode or not match or int(match[1]) != expected_pid:
        raise ValueError("RUNNING_DAEMON_PID_CHANGED")
    result = subprocess.run(["/bin/ps", "-p", str(expected_pid), "-o", "uid=,command="], capture_output=True, text=True, timeout=10)
    row = result.stdout.strip()
    if (result.returncode or not row.startswith("499 ") or "-m uvicorn recase.api:app" not in row
            or "--port 8100" not in row):
        raise ValueError("RUNNING_SERVICE_IDENTITY_CHANGED")
    return account


def inspect_service(expected_pid):
    if os.geteuid() != 0:
        return {"status": "ADMIN_AUTH_REQUIRED", "probe_executed": False, "job_state": "UNKNOWN"}
    account = validate_identity(expected_pid)
    command = [str(Path(sys.executable).resolve()), "-I", "-c", PROBE, str(DATABASE)]
    result = subprocess.run(command, user=account.pw_uid, group=account.pw_gid,
                            extra_groups=os.getgrouplist(SERVICE, account.pw_gid),
                            cwd="/Users/Shared", env={"PATH": "/usr/bin:/bin"},
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        return {"status": "SERVICE_PROBE_FAILED", "probe_executed": False,
                "process_exit_code": result.returncode, "job_state": "UNKNOWN"}
    report = json.loads(result.stdout)
    if report.get("uid") != 499 or report.get("euid") != 499:
        raise ValueError("PROBE_DID_NOT_RUN_AS_SERVICE")
    # Check again after the read; changed processes cannot authorize later work.
    validate_identity(expected_pid)
    return {"status": "DIAGNOSTIC_COMPLETE", "probe_executed": True,
            "service_pid": expected_pid, "database": str(DATABASE), "probe": report,
            "service_mutations": 0, "model_calls": 0,
            "scope": "Metadata and aggregate live read-only query; normal SQLite WAL reader coordination may occur. No repair, restart or deployment."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-pid", required=True, type=int)
    args = parser.parse_args()
    try:
        report = inspect_service(args.expected_pid)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        # Do not echo captured launchctl/config/database content or exception text.
        report = {"status": "DIAGNOSTIC_BLOCKED", "error_type": type(exc).__name__,
                  "reason": str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z_]+", str(exc)) else "INSPECTION_FAILED",
                  "job_state": "UNKNOWN", "model_calls": 0, "service_mutations": 0}
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "DIAGNOSTIC_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
