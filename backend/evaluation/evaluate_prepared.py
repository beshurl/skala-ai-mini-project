"""Live-gated public diagnostics and validation of actually completed NLI candidates."""
import argparse
import fcntl
import importlib.util
import json
import math
import os
import platform
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.experiments import verify_frozen
from recase.ledger import file_digest, read_ledger, utc_now
from recase.paths import PROJECT_ROOT
from recase.prepared_data import load_packet, permitted, read_reviews, rows, verify_dataset_isolation
from scripts.dataset_control import write_new


def model_idle():
    path = PROJECT_ROOT / "runtime/model.lock"
    if not path.exists():
        return True
    try:
        with path.open("r") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def preflight(prepared, dataset, isolation_path):
    from collections import Counter
    from recase.delegated_review import load_delegation, review_kind
    packet, protocol, datasets, items = load_packet(prepared)
    if dataset not in datasets or dataset == "nli_train_candidates":
        raise ValueError("Choose a declared evaluation dataset, never training candidates")
    latest = read_reviews(packet / "reviews/human_reviews.jsonl")
    delegation = load_delegation(packet, items)
    kinds = Counter(review_kind(i, latest.get(i["subject_sha256"]), delegation)
                    for i in items if i["subject"]["input"]["dataset"] == dataset)
    missing = [i["sample_id"] for i in items if i["subject"]["input"]["dataset"] == dataset
               and not review_kind(i, latest.get(i["subject_sha256"]), delegation)]
    proof, error = None, None
    try:
        proof = verify_dataset_isolation(isolation_path, packet, dataset)
    except (OSError, ValueError, PermissionError, KeyError) as exc:
        error = type(exc).__name__ + ": " + str(exc)
    checks = {"authorized_review_and_purpose": not missing, "live_real_answer_os_isolation": proof is not None, "model_idle": model_idle()}
    return {"status": "PASS" if all(checks.values()) else "BLOCKED", "checked_at": utc_now(), "dataset": dataset,
            "checks": checks, "missing_review_count": len(missing), "os_error": error,
            "human_reviewed_count": kinds["human_attestation"], "delegated_ai_review_count": kinds["delegated_ai_review"],
            "answer_proof": proof, "model_loaded": False, "model_calls": 0,
            "scope": "Public development diagnostic/validation; not blind final performance"}


def completed_candidate(cycle_path, training_run):
    cycle = verify_frozen(cycle_path)
    if cycle.get("audit_kind") != "prepared_native_nli_v1":
        raise PermissionError("A native NLI frozen cycle is required")
    run = Path(training_run).resolve(strict=True)
    plan = json.loads((run / "plan.json").read_text())
    events = read_ledger(PROJECT_ROOT / "runtime/training-attempts.jsonl")
    starts = [e for e in events if e["sha256"] == plan["reservation"] and e["payload"].get("action") == "training_started"]
    finished = [e["payload"] for e in events if e["payload"].get("action") == "training_finished"
                and e["payload"].get("reservation") == plan["reservation"]]
    if (plan["cycle"] != cycle["cycle_sha256"] or len(starts) != 1 or not finished
            or starts[0]["payload"].get("cycle_sha256") != cycle["cycle_sha256"]
            or finished[-1].get("status") != "COMPLETED" or finished[-1].get("exit_code") != 0
            or Path(finished[-1]["output"]).resolve() != run):
        raise PermissionError("An actually completed, ledger-bound training candidate is required")
    adapter = run / "adapter"
    if not (adapter / "adapters.safetensors").is_file():
        raise FileNotFoundError("Completed adapter weights missing")
    return cycle, adapter, starts[0]["payload"]["candidate"]


def load_scorer(packet):
    seal = json.loads((packet / "tool_manifest.json").read_text())
    if seal.get("task_metrics.py") != file_digest(packet / "task_metrics.py"):
        raise ValueError("Scorer must be included in the unchanged tool seal")
    spec = importlib.util.spec_from_file_location("recase_sealed_task_metrics", packet / "task_metrics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.score


def evaluate(prepared, dataset, variant, isolation_path, out, cycle_path=None, training_run=None):
    gate = preflight(prepared, dataset, isolation_path)
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_new(out / "preflight.json", gate)
    if gate["status"] != "PASS":
        return 2
    packet, protocol, datasets, _ = load_packet(prepared)
    cycle, candidate = None, None
    if variant == "candidate":
        if dataset != "nli_validation" or not cycle_path or not training_run:
            raise PermissionError("Candidate selection uses nli_validation and a completed frozen training run only")
        cycle, adapter, candidate = completed_candidate(cycle_path, training_run)
        if Path(cycle["audit_inputs"]["prepared"]).resolve() != packet:
            raise PermissionError("Candidate and validation packet differ")
    elif variant in ("base", "existing_ft") and not cycle_path and not training_run:
        adapter = PROJECT_ROOT / "outputs/mlx_adapter" if variant == "existing_ft" else None
    else:
        raise ValueError("Unknown variant or unexpected training arguments")
    from recase.model import LocalModel, SYSTEM
    model = LocalModel(adapter=adapter, max_tokens=protocol["generation"]["max_output_tokens"][datasets[dataset]["spec"]["task"]])
    if model.path.name != protocol["revision"]:
        raise ValueError("Model revision differs from the predeclared packet")
    predictions, attempted = [], 0
    try:
        model.load()
        info = {"dataset": dataset, "task": datasets[dataset]["spec"]["task"], "variant": variant,
                "protocol_sha256": file_digest(packet / "protocol.json"), "scorer_sha256": file_digest(packet / "task_metrics.py"),
                "runner_sha256": file_digest(__file__), "gate_sha256": file_digest(Path(__file__).parents[1] / "recase/prepared_data.py"),
                "input_sha256": datasets[dataset]["spec"]["inputs_sha256"], "answer_sha256": gate["answer_proof"]["answer_sha256"],
                "sample_ids": [i["sample_id"] for i in datasets[dataset]["inputs"]], "model": model.info,
                "cycle_sha256": cycle["cycle_sha256"] if cycle else None, "candidate": candidate,
                "platform": platform.platform(), "started_at": utc_now()}
        write_new(out / "manifest.json", info)
        deadline = time.monotonic() + 1800
        fd = os.open(out / "raw_predictions.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            for inp in datasets[dataset]["inputs"]:
                if time.monotonic() >= deadline:
                    break  # All omitted rows remain in the denominator.
                cancel = threading.Event()
                timer = threading.Timer(180, cancel.set)
                timer.daemon = True
                timer.start()
                row = {"sample_id": inp["sample_id"], "model_call_attempted": False}
                try:
                    prefix = model.tokenizer.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": inp["prompt"]}],
                        tokenize=False, add_generation_prompt=True, enable_thinking=False)
                    if len(model.tokenizer.encode(prefix)) + model.max_tokens > protocol["generation"]["context_tokens"]:
                        raise ValueError("CONTEXT_LIMIT")
                    row["model_call_attempted"] = True
                    attempted += 1
                    row.update(model.infer(inp["prompt"], cancel))
                except Exception as exc:
                    row.update(response="", runtime_error=type(exc).__name__)
                finally:
                    timer.cancel()
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                predictions.append(row)
        score = load_scorer(packet)
        metrics, scored = score(info["task"], datasets[dataset]["inputs"], rows(gate["answer_proof"]["answers"]), predictions)
        metrics.update(identity=info, model_calls=attempted, prompt_tokens=sum(r.get("prompt_tokens", 0) for r in predictions),
                       generation_tokens=sum(r.get("generation_tokens", 0) for r in predictions), ended_at=utc_now())
        from evaluation.scoring import percentile
        measured = [r["seconds"] for r in predictions if "seconds" in r]
        metrics["p95_generation_seconds"] = percentile(measured, .95) if measured else None
        write_new(out / "metrics.json", metrics)
        write_new(out / "scored_predictions.json", scored)
        return 1 if metrics["runtime_failures"] or metrics["missing_predictions"] else 0
    finally:
        model.close()


def compare(paths):
    runs = [json.loads(Path(path).read_text()) for path in paths]
    if len(runs) < 2:
        raise ValueError("At least two actual runs are required")
    a = runs[0]["identity"]
    if not a.get("sample_ids") or len(set(a["sample_ids"])) != len(a["sample_ids"]):
        raise ValueError("Nonempty unique sample IDs required")
    fields = ("dataset", "task", "protocol_sha256", "scorer_sha256", "runner_sha256", "gate_sha256",
              "input_sha256", "answer_sha256", "sample_ids", "platform")
    model_fields = ("model", "revision", "config_sha256", "tokenizer_sha256", "quantization", "prompt_sha256", "generation")
    candidates = []
    for run in runs:
        b = run["identity"]
        if b["variant"] not in {"base", "existing_ft", "candidate"}:
            raise ValueError("Unknown evaluated model variant")
        if any(a[k] != b[k] for k in fields) or any(a["model"][k] != b["model"][k] for k in model_fields):
            raise ValueError("Mismatched task/data/model/protocol/scorer or runner; comparison refused")
        if run["count"] != len(a["sample_ids"]) or run["missing_predictions"] or run["runtime_failures"] or any(run["integrity_errors"].values()):
            raise ValueError("Incomplete or failed run; comparison refused")
        for key in ("accuracy", "macro_f1", "token_overlap_f1", "mean_generation_seconds", "p95_generation_seconds", "model_calls", "prompt_tokens", "generation_tokens"):
            if key in run and run[key] is not None:
                if type(run[key]) not in (int, float) or not math.isfinite(run[key]) or run[key] < 0:
                    raise ValueError("Invalid quality/cost measurement")
                if key in ("accuracy", "macro_f1", "token_overlap_f1") and run[key] > 1:
                    raise ValueError("Quality measurement outside0..1")
        if b["variant"] != "base" and (not b["model"]["adapter_loaded"] or not b["model"]["adapter_sha256"]):
            raise ValueError("Actually loaded adapter identity required")
        if b["variant"] == "base" and (b["model"]["adapter_loaded"] or b["model"]["adapter_sha256"] is not None):
            raise ValueError("Base unexpectedly used an adapter")
        if b["variant"] == "candidate":
            if b["dataset"] != "nli_validation" or not b["cycle_sha256"]:
                raise ValueError("Candidate selection must use frozen nli_validation")
            candidates.append(b)
    if len(candidates) > 3 or len({(c["cycle_sha256"], c["candidate"]) for c in candidates}) != len(candidates):
        raise ValueError("At most three unique candidate runs; duplicate selection rows refused")
    if len({c["cycle_sha256"] for c in candidates}) > 1:
        raise ValueError("Candidate comparison requires the same frozen validation cycle")
    return {"dataset": a["dataset"], "scope": "Matched public development runs only; no automatic model promotion",
            "runs": [{"variant": r["identity"]["variant"], "candidate": r["identity"]["candidate"],
                      **{k: v for k, v in r.items() if isinstance(v, (int, float))}} for r in runs]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("preflight", "evaluate", "compare"))
    p.add_argument("--prepared")
    p.add_argument("--dataset")
    p.add_argument("--isolation-report")
    p.add_argument("--out", required=True)
    p.add_argument("--variant", choices=("base", "existing_ft", "candidate"))
    p.add_argument("--cycle")
    p.add_argument("--training-run")
    p.add_argument("--metrics", nargs="+")
    a = p.parse_args()
    if a.action == "compare":
        if not a.metrics:
            p.error("--metrics with at least two actual run paths required")
        write_new(a.out, compare(a.metrics))
        return 0
    if not a.prepared or not a.dataset or not a.isolation_report:
        p.error("--prepared, --dataset and --isolation-report required")
    if a.action == "preflight":
        result = preflight(a.prepared, a.dataset, a.isolation_report)
        write_new(a.out, result)
        print(json.dumps({"status": result["status"], "checks": result["checks"]}))
        return 0 if result["status"] == "PASS" else 2
    if not a.variant:
        p.error("--variant required for evaluation")
    return evaluate(a.prepared, a.dataset, a.variant, a.isolation_report, a.out, a.cycle, a.training_run)


if __name__ == "__main__":
    raise SystemExit(main())
