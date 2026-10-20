"""Bounded real loopback API/auth/MLX load check; no credentials in artifacts."""
import argparse
import asyncio
import json
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import utc_now
from evaluation.scoring import percentile
from scripts.dataset_control import write_new
import httpx


async def check(url, auth_config, key_file):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ValueError("Only a loopback HTTP root URL is permitted")
    config = json.loads(Path(auth_config).read_text())
    key = Path(key_file).read_text().strip()
    started, clock = utc_now(), time.monotonic()
    async with httpx.AsyncClient(base_url=url, timeout=5, follow_redirects=False) as guest:
        unauth = await guest.get("/health")
        bad = await guest.get("/health", auth=(config["user"], "deliberately-wrong-test-key"))
    assert unauth.status_code == bad.status_code == 401, "Authentication boundary failed"
    clients, jobs, responses = [], [], []
    try:
        for _ in range(6):
            client = httpx.AsyncClient(base_url=url, auth=(config["user"], key), timeout=5, follow_redirects=False)
            clients.append(client)
            health = await client.get("/health")
            assert health.json()["mode"] == "local_personal"
            ready = (await client.get("/ready")).json()
            assert ready["ready"] is True and ready["model"]["backend"] == "mlx" and ready["model"]["adapter_loaded"] is True
            session = (await client.post("/api/demo")).json()
            client.headers["x-recase-csrf"] = session["csrf"]
            cases = (await client.get("/api/cases")).json()
            jobs.extend((client, case["id"]) for case in cases)
        # Verify authentication does not replace per-session ownership or CSRF.
        assert (await clients[1].get("/api/cases/" + jobs[0][1])).status_code == 404
        csrf = clients[0].headers.pop("x-recase-csrf")
        assert (await clients[0].post(f"/api/cases/{jobs[0][1]}/release", json={"evidence_version": 1})).status_code == 403
        clients[0].headers["x-recase-csrf"] = csrf
        request_clock = time.monotonic()
        async def submit(client, case):
            response = await client.post(f"/api/cases/{case}/analyses", json={"evidence_version": 1})
            return client, response
        responses = await asyncio.gather(*(submit(client, case) for client, case in jobs))
        statuses = Counter(response.status_code for _, response in responses)
        assert set(statuses) <= {202, 429} and statuses[429] > 0 and 1 <= statuses[202] <= 9
        pending = {r.json()["id"]: (c, r.json()) for c, r in responses if r.status_code == 202}
        done = []
        while pending:
            if time.monotonic() - request_clock > 60:
                raise TimeoutError("LOCAL_LOAD_BUDGET_60_SECONDS")
            for job_id, (client, _) in list(pending.items()):
                response = await client.get("/api/jobs/" + job_id)
                assert response.status_code == 200
                row = response.json()
                if row["status"] not in {"QUEUED", "RUNNING"}:
                    assert row["status"] == "COMPLETED" and row["result"]["provenance"] == "local_mlx"
                    done.append(row)
                    del pending[job_id]
            await asyncio.sleep(.1)
        terminal_latencies = sorted(row["updated"] - row["created"] for row in done)
        usages = [row["result"]["usage"] for row in done]
        return {"started_at": started, "finished_at": utc_now(), "status": "PASS", "target": "this Mac loopback only",
                "scope": "real MLX/adapter; six synthetic sessions, twelve simultaneous requests; bounded 60s",
                "authentication": {"unauthenticated": unauth.status_code, "wrong_key": bad.status_code,
                                   "valid_key": 200, "foreign_case": 404, "missing_csrf": 403},
                "request_count": len(jobs), "response_codes": dict(statuses), "completed": len(done),
                "terminal_statuses": dict(Counter(row["status"] for row in done)),
                "wall_seconds": time.monotonic() - clock,
                "job_latency_including_queue_s": {"p50": percentile(terminal_latencies, .5),
                                                   "p95": percentile(terminal_latencies, .95), "max": terminal_latencies[-1]},
                "job_latencies_s": terminal_latencies, "job_ids": [row["id"] for row in done],
                "model_calls": sum(u["model_calls"] for u in usages),
                "prompt_tokens": sum(u["prompt_tokens"] for u in usages),
                "generation_tokens": sum(u["generation_tokens"] for u in usages),
                "model_identity": ready["model"],
                "limitations": ["Not multiuser/remote/TLS/auth-provider validation or sustained-load capacity.",
                                "Synthetic data only; this does not measure case-analysis quality."]}
    finally:
        # On failure, cancel only jobs that THIS check submitted, never other work.
        for client, response in responses:
            if response.status_code == 202:
                try:
                    await client.post("/api/jobs/" + response.json()["id"] + "/cancel")
                except httpx.HTTPError:
                    pass
        for client in clients:
            await client.aclose()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://127.0.0.1:8100")
    for key in ("auth-config", "key-file", "out"):
        p.add_argument("--" + key, required=True)
    args = p.parse_args()
    report = asyncio.run(check(args.url, args.auth_config, args.key_file))
    write_new(args.out, report)
    print(json.dumps({"status": report["status"], "responses": report["response_codes"], "completed": report["completed"], "out": args.out}))


if __name__ == "__main__":
    main()
