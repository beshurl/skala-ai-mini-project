"""Predeclared app/MCP development evaluation; AI references are not gold.

Preparation never loads model weights. Real inference requires the shared model
lock to be free. This tool cannot pause or restart the production service.
"""
import argparse
import fcntl
import json
import importlib.metadata
import os
import platform
import secrets
import signal
import stat
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.contracts import AnalysisResult
from recase.ledger import digest, file_digest, utc_now
from recase.model import MODEL_ID, LocalModel, resolve_model
from recase.paths import BACKEND_ROOT, PROJECT_ROOT
from recase.practice import BUNDLE

REFERENCE = PROJECT_ROOT / "docs/practice/v1/review_reference.json"
LOCK = PROJECT_ROOT / "runtime/model.lock"
LIMITS = {"stages": 36, "seconds_per_job": 180, "seconds_per_variant": 1800,
          "maximum_model_calls_per_variant": 36, "generation_tokens": 1024,
          "context_tokens": 4096, "consecutive_invalid_stop": 3, "automatic_retries": 0}


def runtime_identity():
    return {"platform": platform.platform(), "python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("mlx", "mlx-lm", "transformers", "tokenizers", "fastapi", "langgraph", "mcp")}}


def write(path, value):
    with Path(path).open("x", encoding="utf8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    Path(path).chmod(0o600)


def stage_id(case_id, version):
    return case_id + ":v" + str(version)


def model_identity():
    path = resolve_model()
    adapter = PROJECT_ROOT / "outputs/mlx_adapter"
    files = [path / n for n in ("config.json", "tokenizer.json", "tokenizer_config.json")]
    files += sorted(path.glob("*.safetensors"))
    files += [adapter / n for n in ("adapter_config.json", "adapters.safetensors")]
    return {"model": MODEL_ID, "revision": path.name, "cache_path": str(path), "adapter": str(adapter)}, files


def prepare(out):
    data, reference = json.loads(BUNDLE.read_text()), json.loads(REFERENCE.read_text())
    if (data.get("source") != "AI_AUTHORED_SYNTHETIC" or data.get("training_eligible") is not False
            or reference.get("human_reviewed") is not False or reference.get("independent_final_set") is not False
            or reference.get("actual_cases") != 0 or reference.get("kind") != "AI_PROPOSED_HUMAN_REVIEW_REFERENCE"):
        raise ValueError("EXPOSED_SYNTHETIC_DEVELOPMENT_ONLY")
    expected = [stage_id(c["id"], s["version"]) for c in data["cases"] for s in c["stages"]]
    refs = {stage_id(r["case_id"], r["version"]): r for r in reference["checks"]}
    if (len(data["cases"]) != 12 or len(expected) != 36 or len(set(expected)) != 36
            or len(reference["checks"]) != 36 or set(refs) != set(expected)
            or any(len(c["claims"]) != 1 for c in data["cases"])):
        raise ValueError("EXACT_12_CASE_36_SINGLE_CLAIM_STAGES_REQUIRED")
    for case in data["cases"]:
        for stage in case["stages"]:
            ref = refs[stage_id(case["id"], stage["version"])]
            public = {e["key"] for e in case["evidence"] if e["release_at"] <= stage["version"]}
            if (ref["proposed_relation"] not in {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT"}
                    or not set(ref["supporting_document_keys"]).issubset(public)):
                raise ValueError("REFERENCE_SCOPE_OR_RELATION_INVALID")
    identity, model_files = model_identity()
    paths = [BUNDLE, REFERENCE, Path(__file__), BACKEND_ROOT / "requirements-lock-macos-arm64.txt"]
    paths += sorted((BACKEND_ROOT / "recase").glob("*.py")) + model_files
    plan = {"kind": "recase-reasoning-development-v1", "created_at": utc_now(),
            "source": "AI_AUTHORED_EXPOSED_DEVELOPMENT", "human_reviewed": False,
            "independent_final_set": False, "statistically_independent_cases": False,
            "contract": "evidence-reasoning-v1", "input": str(BUNDLE), "reference": str(REFERENCE),
            "sample_ids": expected, "variants": ["base", "existing_ft"], "limits": LIMITS,
            "model_identity": identity,
            "runtime_identity": runtime_identity(),
            "shared_lock": {"path": str(LOCK), "device": LOCK.stat().st_dev, "inode": LOCK.stat().st_ino},
            "bound_files": [{"path": str(p), "sha256": file_digest(p)} for p in dict.fromkeys(paths)],
            "metrics": ["complete_and_missing_stages", "valid_result_fraction_over_36", "exact_public_quote_checks",
                        "ai_proposed_relation_agreement_over_36", "wall_time_and_calls", "partial_and_failure_counts"],
            "not_measured": ["semantic_citation_accuracy", "hypothesis_quality", "human_review", "real_case_accuracy"],
            "policy": "No retry/adapter selection/training. Stop after runtime failure or3 consecutive invalid stages; remaining stages stay in denominator. Read AI references only after inference worker exits."}
    plan["plan_sha256"] = digest(plan)
    out = Path(out).absolute()
    out.mkdir(mode=0o700)
    write(out / "plan.json", plan)
    return plan


def checked_plan(path):
    path = Path(path).absolute()
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077
            or path.is_symlink()):
        raise PermissionError("PRIVATE_OPERATOR_PLAN_REQUIRED")
    plan = json.loads(path.read_text())
    if (plan.get("plan_sha256") != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            or plan.get("kind") != "recase-reasoning-development-v1" or plan.get("limits") != LIMITS
            or plan.get("variants") != ["base", "existing_ft"] or plan.get("human_reviewed") is not False
            or plan.get("independent_final_set") is not False):
        raise ValueError("PLAN_CHANGED_OR_UNSUPPORTED")
    for ref in plan["bound_files"]:
        if file_digest(ref["path"]) != ref["sha256"]:
            raise PermissionError("PLAN_BOUND_SOURCE_DATA_OR_MODEL_CHANGED")
    if runtime_identity() != plan["runtime_identity"]:
        raise PermissionError("INSTALLED_RUNTIME_CHANGED")
    lock = Path(plan["shared_lock"]["path"]).stat()
    if (lock.st_dev, lock.st_ino) != (plan["shared_lock"]["device"], plan["shared_lock"]["inode"]):
        raise PermissionError("ORIGINAL_MODEL_LOCK_CHANGED")
    return plan


def preflight(plan, backend):
    if backend == "mlx" and os.geteuid() == 0:
        return {"status": "BLOCKED_RUN_AS_NONROOT_EVALUATOR", "model_loaded": False, "model_calls": 0}
    idle = False
    if backend == "mlx":
        try:
            with Path(plan["shared_lock"]["path"]).open("r") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(lock, fcntl.LOCK_UN)
                idle = True
        except BlockingIOError:
            pass
    return {"status": "PASS" if backend == "fixture" or idle else "BLOCKED_MODEL_BUSY",
            "checked_at": utc_now(), "backend": backend, "real_model_idle": idle if backend == "mlx" else "NOT_CHECKED_FIXTURE_ONLY",
            "model_loaded": False, "model_calls": 0, "training_runs": 0}


def worker(plan_path, variant, backend, out):
    """One process/one model; same app API, worker and stdio MCP as the UI."""
    plan, out = checked_plan(plan_path), Path(out)
    if variant not in plan["variants"] or backend not in {"fixture", "mlx"}:
        raise ValueError("PREDECLARED_VARIANT_AND_BACKEND_REQUIRED")
    marker = out / "execution-marker.json"
    allowed = {"execution-marker.json", "plan-copy.json", "preflight.json", "worker.log", "worker-process.json"}
    if (out.stat().st_uid != os.geteuid() or out.stat().st_mode & 0o077
            or any(p.name not in allowed or p.is_symlink() for p in out.iterdir())
            or json.loads(marker.read_text()).get("plan_sha256") != plan["plan_sha256"]):
        raise PermissionError("FRESH_PRIVATE_RUN_DIRECTORY_REQUIRED")
    gate = preflight(plan, backend)
    if gate["status"] != "PASS":
        write(out / "worker-blocked.json", gate)
        return 2
    # No evaluator reference parsing takes place in this function.
    data = json.loads(Path(plan["input"]).read_text())
    if backend == "fixture":
        from recase.testing import FixtureModel
        model = FixtureModel()
    else:
        model = LocalModel(model=plan["model_identity"]["cache_path"],
                           adapter=plan["model_identity"]["adapter"] if variant == "existing_ft" else None)
    from fastapi.testclient import TestClient
    from recase.api import create_app
    started, invalid = time.monotonic(), 0
    app = create_app(out / "cases.db", model, testing=True, accounts_path=out / "accounts.db")
    with TestClient(app) as client, (out / "predictions.jsonl").open("x") as stream:
        if not app.state.ready:
            write(out / "worker-failure.json", {"reason": "MODEL_OR_APP_NOT_READY"})
            return 2
        registration = client.post("/api/auth/register", json={"name": "SYNTHETIC_EVALUATION_ONLY",
            "email": secrets.token_hex(12) + "@example.invalid", "password": secrets.token_urlsafe(24)})
        if registration.status_code != 201:
            raise RuntimeError("SYNTHETIC_ACCOUNT_CREATION_FAILED")
        client.headers["x-recase-csrf"] = registration.json()["csrf"]
        seeded = client.post("/api/practice/general")
        if seeded.status_code != 201:
            raise RuntimeError("EXPLICIT_PRACTICE_CREATION_FAILED")
        write(out / "worker-identity.json", {"model": model.info, "variant": variant, "backend": backend,
                                             "evaluator_uid": os.geteuid(), "actual_uid499_deployment": False})
        for case, case_id in zip(data["cases"], seeded.json()["case_ids"], strict=True):
            for stage in case["stages"]:
                if time.monotonic() - started >= LIMITS["seconds_per_variant"] - LIMITS["seconds_per_job"]:
                    return 3
                version = stage["version"]
                if version > 1:
                    released = client.post(f"/api/cases/{case_id}/release", json={"evidence_version": version - 1})
                    if released.status_code != 200:
                        raise RuntimeError("STAGE_RELEASE_FAILED")
                snapshot = client.get("/api/cases/" + case_id).json()
                public = {e["origin"]["document_id"]: e for e in case["evidence"] if e["release_at"] <= version}
                mapping = {e["id"]: public[e["attributes"]["source_document"]]["key"] for e in snapshot["evidence"]}
                if (snapshot["evidence_version"] != version or len(mapping) != len(public)
                        or any(e["text"] != public[e["attributes"]["source_document"]]["text"] for e in snapshot["evidence"])):
                    raise RuntimeError("ACTUAL_PUBLIC_SNAPSHOT_DIFFERS_FROM_PLAN")
                request_started = time.monotonic()
                response = client.post(f"/api/cases/{case_id}/analyses", json={"evidence_version": version})
                if response.status_code != 202:
                    raise RuntimeError("ANALYSIS_SUBMISSION_FAILED")
                job_id = response.json()["id"]
                while True:
                    job = client.get("/api/jobs/" + job_id).json()
                    if job["status"] not in {"QUEUED", "RUNNING"}:
                        break
                    if time.monotonic() - request_started > LIMITS["seconds_per_job"] + 10:
                        client.post("/api/jobs/" + job_id + "/cancel")
                        raise TimeoutError("TERMINAL_STATE_NOT_OBSERVED")
                    time.sleep(.02)
                row = {"sample_id": stage_id(case["id"], version), "service_case_id": case_id,
                       "version": version, "job_status": job["status"], "error": job["error"],
                       "claim_ids": [c["id"] for c in snapshot["claims"]], "evidence_map": mapping,
                       "result": job["result"], "wall_seconds": time.monotonic() - request_started,
                       "model_calls_attempted_observed": client.get("/api/jobs/" + job_id + "/events").text.count("event: general_model_started")}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n");stream.flush();os.fsync(stream.fileno())
                with (out / "progress.jsonl").open("a") as progress:
                    progress.write(json.dumps({"at": utc_now(), "sample_id": row["sample_id"], "status": row["job_status"]}) + "\n")
                limitations = (job.get("result") or {}).get("limitations", [])
                invalid = 0 if job["status"] == "COMPLETED" else invalid + 1
                if (job["status"] in {"FAILED", "CANCELLED", "STALE"} or "GENERAL_MODEL_FAILED" in limitations
                        or invalid >= LIMITS["consecutive_invalid_stop"]):
                    return 3
    return 0


def citations(value):
    if isinstance(value, dict):
        if {"evidence_id", "quote"}.issubset(value):
            yield value
        for child in value.values():
            yield from citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from citations(child)


def model_matches(info, plan, backend, variant):
    if backend == "fixture":
        return info.get("backend") == "fixture"
    expected = plan["model_identity"]
    hashes = {r["path"]: r["sha256"] for r in plan["bound_files"]}
    adapter = str(Path(expected["adapter"]) / "adapters.safetensors")
    return (info.get("backend") == "mlx" and info.get("model") == expected["model"]
            and info.get("revision") == expected["revision"]
            and info.get("config_sha256") == hashes[str(Path(expected["cache_path"]) / "config.json")]
            and info.get("tokenizer_sha256") == hashes[str(Path(expected["cache_path"]) / "tokenizer.json")]
            and info.get("adapter_loaded") is (variant == "existing_ft")
            and info.get("adapter_sha256") == (hashes[adapter] if variant == "existing_ft" else None))


def score(plan, records, backend, variant, worker_exit):
    """Agreement with exposed AI proposals; never independent accuracy."""
    hashes = {r["path"]: r["sha256"] for r in plan["bound_files"]}
    if any(file_digest(plan[name]) != hashes[plan[name]] for name in ("input", "reference")):
        raise PermissionError("SCORING_INPUT_OR_REFERENCE_CHANGED")
    data = json.loads(Path(plan["input"]).read_text())
    reference = json.loads(Path(plan["reference"]).read_text())
    refs = {stage_id(r["case_id"], r["version"]): r for r in reference["checks"]}
    cases = {c["id"]: c for c in data["cases"]}
    counts = Counter(r["sample_id"] for r in records)
    rows = {r["sample_id"]: r for r in records if counts[r["sample_id"]] == 1}
    statuses, errors = Counter(), Counter()
    valid = agreed = quote_total = quote_valid = 0
    unique_quotes = set()
    stage_results = []
    for sample_id in plan["sample_ids"]:
        row = rows.get(sample_id)
        item = {"sample_id": sample_id, "status": "NOT_RUN", "valid": False, "reference_relation_agreement": False}
        if row:
            item["status"] = row.get("job_status", "INVALID_RECORD")
            try:
                result = AnalysisResult.model_validate(row["result"])
                expected_version = int(sample_id.split(":v")[1])
                public = {e["key"]: e for e in cases[sample_id.split(":")[0]]["evidence"] if e["release_at"] <= expected_version}
                spans = list(citations(result.model_dump()))
                span_checks = []
                for citation in spans:
                    quote_total += 1
                    text = public[row["evidence_map"][citation["evidence_id"]]]["text"]
                    a, b = citation.get("start"), citation.get("end")
                    unique_quotes.add((citation["evidence_id"], a, b))
                    passed = type(a) is int and type(b) is int and 0 <= a < b <= len(text) and text[a:b] == citation["quote"]
                    quote_valid += int(passed);span_checks.append(passed)
                checks = [row["job_status"] == "COMPLETED", result.analysis_contract_version == plan["contract"],
                          row["version"] == expected_version,
                          result.case_id == row["service_case_id"], result.evidence_version == row["version"],
                          len(result.findings) == len(result.reasoning.reviews) == len(row["claim_ids"]) == 1,
                          {f.claim_id for f in result.findings} == set(row["claim_ids"]),
                          result.reasoning.reviews[0].status == "SOURCE_CHECKED_MODEL_ASSESSMENT",
                          all(span_checks), set(row["evidence_map"].values()) == set(public), len(row["evidence_map"]) == len(public),
                          model_matches(result.model, plan, backend, variant),
                          result.reasoning.generation_max_tokens == LIMITS["generation_tokens"],
                          result.reasoning.model_calls_attempted == row["model_calls_attempted_observed"] == 1,
                          result.provenance == ("local_mlx" if backend == "mlx" else "deterministic_fixture")]
                item.update(valid=all(checks), observed_relation=result.findings[0].label,
                            reference_relation_agreement=all(checks) and result.findings[0].label == refs[sample_id]["proposed_relation"],
                            quotes_checked=len(spans), quotes_valid=sum(span_checks),
                            model_calls_attempted=result.reasoning.model_calls_attempted)
                valid += int(item["valid"]);agreed += int(item["reference_relation_agreement"])
                errors.update(code for code in result.limitations if code.startswith("GENERAL_"))
            except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                item["validation_error"] = "RESULT_OR_PUBLIC_QUOTE_INVALID"
        statuses[item["status"]] += 1
        stage_results.append(item)
    return {"kind": "exposed_reasoning_development_metrics_v1", "plan_sha256": plan["plan_sha256"],
            "backend": backend, "variant": variant, "worker_exit_code": worker_exit,
            "denominator": len(plan["sample_ids"]), "submitted_unique_stages": len(set(rows).intersection(plan["sample_ids"])),
            "missing_or_duplicate_stages": sum(r["status"] == "NOT_RUN" for r in stage_results),
            "statuses": dict(statuses), "valid_stages": valid, "valid_fraction": valid / len(plan["sample_ids"]),
            "ai_proposed_relation_agreement": agreed / len(plan["sample_ids"]) if backend == "mlx" and records else None,
            "exact_quote_checks": {"checked": quote_total, "valid": quote_valid, "unique_source_spans": len(unique_quotes)}, "validation_codes": dict(errors),
            "model_calls_attempted_observed": sum(r.get("model_calls_attempted_observed", 0) for r in records),
            "recorded_wall_seconds": sum(r.get("wall_seconds", 0) for r in records),
            "recorded_prompt_tokens": sum((r.get("result") or {}).get("usage", {}).get("prompt_tokens", 0) for r in records),
            "recorded_generation_tokens": sum((r.get("result") or {}).get("usage", {}).get("generation_tokens", 0) for r in records),
            "unrecorded_inflight_usage": "NOT_MEASURED" if worker_exit != 0 else "NONE_ON_COMPLETE_WORKER_EXIT",
            "duplicate_ids": [key for key, n in counts.items() if n > 1],
            "unexpected_ids": sorted(set(counts) - set(plan["sample_ids"])), "stages": stage_results,
            "independent_final_accuracy": "NOT_MEASURED", "semantic_citation_accuracy": "NOT_MEASURED",
            "human_semantic_review": "PENDING", "actual_uid499_deployment": False,
            "scope": "Exposed AI-authored synthetic development proposals. Fixture metrics are execution checks only; these cases are not statistically independent."}


def execute(plan_path, variant, backend, out):
    plan = checked_plan(plan_path)
    if variant not in plan["variants"] or backend not in {"fixture", "mlx"}:
        raise ValueError("PREDECLARED_VARIANT_AND_BACKEND_REQUIRED")
    out = Path(out).absolute();out.mkdir(mode=0o700)
    gate = preflight(plan, backend);write(out / "preflight.json", gate)
    write(out / "plan-copy.json", plan)
    write(out / "execution-marker.json", {"kind": "fresh_reasoning_run", "plan_sha256": plan["plan_sha256"]})
    code = 2
    supervisor_terminated = False
    if gate["status"] == "PASS":
        env = dict(os.environ)
        for key in ("RECASE_AUTH_FILE", "RECASE_ADMIN_AUTH_FILE", "RECASE_DB", "RECASE_ACCOUNTS_DB",
                    "RECASE_DELETIONS", "RECASE_ADAPTER", "RECASE_REFERENCE_CORPUS", "RECASE_REFERENCE_REVIEWS"):
            env.pop(key, None)
        env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                   WANDB_MODE="disabled", LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false", OTEL_SDK_DISABLED="true")
        command = [sys.executable, str(Path(__file__).absolute()), "worker", "--plan", str(Path(plan_path).absolute()),
                   "--variant", variant, "--backend", backend, "--out", str(out)]
        with (out / "worker.log").open("x") as log:
            process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            write(out / "worker-process.json", {"pid": process.pid, "uid": os.geteuid(), "command": command, "started_at": utc_now()})
            try:
                code = process.wait(timeout=LIMITS["seconds_per_variant"] + 30)
            except subprocess.TimeoutExpired:
                stop_worker(process)
                supervisor_terminated = True
                code = 3
            except KeyboardInterrupt:
                stop_worker(process)
                supervisor_terminated = True
                code = 130
    try:
        after = checked_plan(plan_path)
        if after["plan_sha256"] != plan["plan_sha256"]:
            raise PermissionError("PLAN_CHANGED_DURING_RUN")
    except (OSError, ValueError, PermissionError):
        write(out / "scoring-refused.json", {"status": "SOURCE_MODEL_OR_PLAN_CHANGED", "denominator": 36,
                                              "model_worker_exit_code": code, "scored": False})
        raise
    path = out / "predictions.jsonl"
    records = []
    for i, line in enumerate(path.read_text().splitlines() if path.exists() else []):
        try:
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("sample_id"), str):
                raise ValueError("INVALID_RECORD")
        except (ValueError, TypeError):
            row = {"sample_id": "MALFORMED_LINE_" + str(i), "job_status": "INVALID_RECORD"}
        records.append(row)
    metrics = score(plan, records, backend, variant, code)
    metrics["supervisor_terminated_worker"] = supervisor_terminated
    write(out / "metrics.json", metrics)
    return metrics


def stop_worker(process):
    """Only the process group created for this worker; never the live daemon."""
    try:os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:pass
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait(timeout=5)


def compare(paths):
    values = [json.loads(Path(p).read_text()) for p in paths]
    if len(values) != 2 or {v["variant"] for v in values} != {"base", "existing_ft"}:
        raise ValueError("TWO_PREDECLARED_VARIANTS_REQUIRED")
    if len({v["plan_sha256"] for v in values}) != 1:
        raise ValueError("MISMATCHED_PLANS")
    if any(v["backend"] != "mlx" or v["valid_stages"] != 36 or v["worker_exit_code"] != 0
           or v["duplicate_ids"] or v["unexpected_ids"] for v in values):
        raise ValueError("REAL_COMPLETE_MATCHED_RUNS_REQUIRED")
    return {"kind": "exposed_development_comparison", "plan_sha256": values[0]["plan_sha256"],
            "results": {v["variant"]: v["ai_proposed_relation_agreement"] for v in values},
            "adapter_promotion": False, "independent_final_accuracy": "NOT_MEASURED",
            "scope": "AI proposal agreement only; neither real-case accuracy nor A-F ablation."}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "worker", "compare"])
    parser.add_argument("--plan");parser.add_argument("--out")
    parser.add_argument("--variant", choices=["base", "existing_ft"])
    parser.add_argument("--backend", choices=["mlx", "fixture"], default="mlx")
    parser.add_argument("--metrics", nargs="+")
    args = parser.parse_args()
    if args.action == "prepare":
        value = prepare(args.out)
        print(json.dumps({"status": "PREDECLARED", "stages": 36, "plan_sha256": value["plan_sha256"], "model_calls": 0}))
    elif args.action == "worker":
        return worker(args.plan, args.variant, args.backend, args.out)
    elif args.action == "compare":
        value = compare(args.metrics);write(args.out, value);print(json.dumps(value))
    else:
        value = execute(args.plan, args.variant, args.backend, args.out)
        print(json.dumps({k: v for k, v in value.items() if k != "stages"}, ensure_ascii=False))
        return 0 if value["valid_stages"] == 36 and value["worker_exit_code"] == 0 else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
