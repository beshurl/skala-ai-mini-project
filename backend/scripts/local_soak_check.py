"""Bounded sequential synthetic loopback soak; stop at the first stalled job."""
import argparse
import asyncio
import json
import getpass
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from recase.ledger import utc_now
from evaluation.scoring import percentile
from scripts.dataset_control import write_new


def validate(url, duration, interval, max_jobs, job_timeout):
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Only a loopback HTTP root URL is permitted")
    if not (0 < duration <= 3600 and 0 < interval <= 600 and 1 <= max_jobs <= 360 and 0 < job_timeout <= 180):
        raise ValueError("Bounded duration/interval/job count/timeout required")


def process_sample(pid, expected_uid):
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "uid=,rss=,pcpu="], capture_output=True, text=True, timeout=3)
    fields = result.stdout.split()
    if result.returncode or len(fields) != 3 or int(fields[0]) != expected_uid or expected_uid == 0:
        raise RuntimeError("SERVICE_PROCESS_IDENTITY_CHANGED")
    return {"uid": int(fields[0]), "rss_kib": int(fields[1]), "cpu_percent": float(fields[2])}


async def run(url, auth, pid, uid, duration=600, interval=10, max_jobs=60, job_timeout=30, *, transport=None, account_credentials=None):
    validate(url, duration, interval, max_jobs, job_timeout)
    clock = time.monotonic()
    report = {"status": "RUNNING", "started_at": utc_now(), "target": url, "service_pid": pid, "service_uid": uid,
              "scope": "Sequential synthetic application operational soak, not dataset quality/final evaluation",
              "requested_window_seconds": duration, "interval_seconds": interval, "max_jobs": max_jobs,
              "job_timeout_seconds": job_timeout, "jobs": [], "submitted_jobs": [], "samples": [], "model_calls": 0,
              "model_call_count_scope": "Completed-job usage only; unfinished job calls are unmeasured",
              "source_text_or_credentials_in_report": False, "training_runs": 0, "service_restarts": 0}
    report["authentication_mode"] = "account-password" if account_credentials else "legacy-personal-access-key"
    active = None
    async with httpx.AsyncClient(base_url=url, auth=auth, timeout=5, follow_redirects=False, transport=transport) as client:
        try:
            process_sample(pid, uid)
            health = await client.get("/health")
            health.raise_for_status()
            expected_mode = "local_accounts" if account_credentials else "local_personal"
            if health.json().get("mode") != expected_mode:
                raise RuntimeError("AUTHENTICATION_MODE_MISMATCH")
            if account_credentials:
                login = await client.post("/api/auth/login", json=account_credentials)
                login.raise_for_status()
                client.headers["x-recase-csrf"] = login.json()["csrf"]
            ready_response = await client.get("/ready")
            ready_response.raise_for_status()
            ready = ready_response.json()
            if not ready.get("ready") or ready.get("model", {}).get("backend") != "mlx" or not ready["model"].get("adapter_loaded"):
                raise RuntimeError("REAL_MLX_ADAPTER_READY_REQUIRED")
            report["model_identity"] = ready["model"]
            # A fresh client gets only its own new synthetic session/cases.
            demo = await client.post("/api/demo/new" if account_credentials else "/api/demo")
            demo.raise_for_status()
            client.headers["x-recase-csrf"] = demo.json()["csrf"]
            cases = await client.get("/api/cases")
            cases.raise_for_status()
            case = cases.json()[0]["id"]
            snapshot = await client.get("/api/cases/" + case)
            snapshot.raise_for_status()
            if snapshot.json().get("source") != "synthetic_fixture":
                raise RuntimeError("SYNTHETIC_CASE_REQUIRED")
            next_due = clock
            while time.monotonic() - clock < duration:
                sample = process_sample(pid, uid)
                sample["elapsed_seconds"] = time.monotonic() - clock
                report["samples"].append(sample)
                state = await client.get("/ready")
                state.raise_for_status()
                if state.json().get("ready") is not True or state.json().get("model") != report["model_identity"]:
                    raise RuntimeError("MODEL_READINESS_OR_IDENTITY_CHANGED")
                if len(report["jobs"]) < max_jobs:
                    response = await client.post(f"/api/cases/{case}/analyses", json={"evidence_version": 1})
                    response.raise_for_status()
                    active = response.json()["id"]
                    report["submitted_jobs"].append({"id": active, "last_status": response.json().get("status", "SUBMITTED")})
                    submitted = time.monotonic()
                    while True:
                        if time.monotonic() - submitted >= job_timeout:
                            raise TimeoutError("NO_JOB_PROGRESS_WITHIN_BUDGET")
                        response = await client.get("/api/jobs/" + active)
                        response.raise_for_status()
                        job = response.json()
                        report["submitted_jobs"][-1]["last_status"] = job["status"]
                        if job["status"] not in {"QUEUED", "RUNNING"}:
                            elapsed = time.monotonic() - submitted
                            report["jobs"].append({"id": active, "status": job["status"], "wall_seconds": elapsed})
                            if job["status"] != "COMPLETED" or job.get("result", {}).get("provenance") != "local_mlx":
                                raise RuntimeError("NON_COMPLETED_REAL_MODEL_JOB")
                            usage = job["result"]["usage"]
                            if usage.get("model_calls", 0) < 1:
                                raise RuntimeError("ACTUAL_MODEL_CALL_REQUIRED")
                            report["model_calls"] += usage["model_calls"]
                            active = None
                            break
                        await asyncio.sleep(min(.2, job_timeout / 4))
                next_due += interval
                await asyncio.sleep(max(0, min(clock + duration, next_due) - time.monotonic()))
            if not report["jobs"]:
                raise RuntimeError("NO_COMPLETED_JOBS")
            report["status"] = "PASS"
        except (httpx.HTTPError, OSError, ValueError, KeyError, IndexError, RuntimeError, TimeoutError) as error:
            report.update(status="FAIL", error_type=type(error).__name__,
                          error_code=str(error) if isinstance(error, (RuntimeError, TimeoutError)) else "REQUEST_OR_PROCESS_CHECK_FAILED")
        finally:
            if active:
                # Never cancel another owner's or an existing job.
                try:
                    cancelled = await client.post("/api/jobs/" + active + "/cancel")
                    report["cancel_only_own_job"] = {"id": active, "http_status": cancelled.status_code}
                except httpx.HTTPError:
                    report["cancel_only_own_job"] = {"id": active, "http_status": None}
            if account_credentials and "x-recase-csrf" in client.headers:
                try:
                    await client.post("/api/auth/logout")
                except httpx.HTTPError:
                    pass
            report.update(finished_at=utc_now(), elapsed_seconds=time.monotonic() - clock,
                          completed_jobs=sum(j["status"] == "COMPLETED" for j in report["jobs"]),
                          total_model_calls=None if active else report["model_calls"],
                          full_requested_window_observed=time.monotonic() - clock >= duration)
            latencies = [j["wall_seconds"] for j in report["jobs"] if j["status"] == "COMPLETED"]
            report["job_latency_p95_seconds"] = percentile(latencies, .95) if latencies else None
            rss = [s["rss_kib"] for s in report["samples"]]
            report["rss_peak_kib"] = max(rss) if rss else None
            report["limitations"] = ["RSS is one process sample, not total Metal/unified-memory allocation.",
                                     "Sequential repeated synthetic case; not maximum throughput or independent case quality.",
                                     "A failed progress probe stops further inference; do not loop retries or restart other work."]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8100")
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument("--auth-config", help="Legacy deployed access-key service only")
    auth_group.add_argument("--email", help="Current account service; password is prompted privately")
    parser.add_argument("--key-file")
    parser.add_argument("--service-pid", required=True, type=int)
    parser.add_argument("--service-uid", required=True, type=int)
    parser.add_argument("--duration", type=int, default=600)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--max-jobs", type=int, default=60)
    parser.add_argument("--job-timeout", type=int, default=30)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    # Check output and bounds before any network request/model job.
    if Path(args.out).exists():
        raise FileExistsError("Use a new result path")
    validate(args.url, args.duration, args.interval, args.max_jobs, args.job_timeout)
    credentials, auth = None, None
    if args.email:
        if args.key_file or not sys.stdin.isatty():
            parser.error("Account passwords must be entered in your local terminal; no key file or piped password")
        credentials = {"email": args.email, "password": getpass.getpass("계정 비밀번호: ")}
    else:
        if not args.key_file:
            parser.error("Legacy service requires --key-file")
        config = json.loads(Path(args.auth_config).read_text())
        auth = (config["user"], Path(args.key_file).read_text().strip())
    try:
        report = asyncio.run(run(args.url, auth, args.service_pid, args.service_uid,
                                args.duration, args.interval, args.max_jobs, args.job_timeout, account_credentials=credentials))
    finally:
        if credentials:
            credentials.clear()
        auth = None
    write_new(args.out, report)
    print(json.dumps({"status": report["status"], "completed_jobs": report["completed_jobs"],
                      "elapsed_seconds": report["elapsed_seconds"], "out": args.out}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
