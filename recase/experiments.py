"""Frozen local experiments and a persistent three-attempt improvement budget."""
import json
import math
import re
from pathlib import Path

from recase.ledger import append_locked, file_digest, locked_records, utc_now

IMPROVEMENT_CYCLE = "post-legacy-independent-v1"
MAX_CANDIDATES = 3
ARMS = {
    "A": {"adapter": False, "rag": False, "agent": False},
    "B": {"adapter": True, "rag": False, "agent": False},
    "C": {"adapter": False, "rag": True, "agent": False},
    "D": {"adapter": True, "rag": True, "agent": False},
    "E": {"adapter": False, "rag": True, "agent": True},
    "F": {"adapter": True, "rag": True, "agent": True},
}
MATCHED_FIELDS = ("sample_ids", "public_evidence_sha256", "reference_scope_sha256", "model_revision",
                  "model_id", "config_sha256", "tokenizer_sha256", "chat_template_sha256",
                  "quantization", "generation", "output_contract", "repair_policy", "platform", "scorer_sha256",
                  "frozen_selection_sha256", "final_dataset_sha256", "protocol_sha256")


def candidate_configs(configs):
    if not isinstance(configs, list) or not 1 <= len(configs) <= MAX_CANDIDATES:
        raise ValueError("Declare 1..3 candidates before training")
    names = set()
    for candidate in configs:
        if set(candidate) != {"id", "iters", "learning_rate", "rank", "layers", "sequence_length"}:
            raise ValueError("Complete explicit candidate configuration required")
        if not re.fullmatch(r"[a-z0-9-]{1,32}", candidate["id"]) or candidate["id"] in names:
            raise ValueError("Unique safe candidate id required")
        if candidate["rank"] != 8 or candidate["layers"] != 8 or candidate["sequence_length"] != 768:
            raise ValueError("Initial cycle is limited to rank8/layers8/sequence768")
        if type(candidate["iters"]) is not int or not 1 <= candidate["iters"] <= 120 or candidate["learning_rate"] not in (1e-4, 5e-5):
            raise ValueError("Candidate outside bounded iteration/learning-rate budget")
        names.add(candidate["id"])
    return configs


def reserve_candidate(path, cycle, candidate_id):
    if cycle.get("state") != "FROZEN" or cycle.get("improvement_cycle") != IMPROVEMENT_CYCLE:
        raise PermissionError("A reviewed frozen cycle is required")
    candidate_configs(cycle["candidates"])
    if candidate_id not in {c["id"] for c in cycle["candidates"]}:
        raise PermissionError("Undeclared training candidate")
    with locked_records(path, create=True) as (stream, rows):
        attempts = [e["payload"] for e in rows if e["payload"].get("action") == "training_started"
                    and e["payload"].get("improvement_cycle") == IMPROVEMENT_CYCLE]
        if len(attempts) >= MAX_CANDIDATES:
            raise PermissionError("TRAINING_BUDGET_EXHAUSTED: failures/timeouts count; no automatic fourth attempt")
        if any(e["candidate"] == candidate_id for e in attempts):
            raise PermissionError("Candidate already attempted; preserve its failure/result")
        return append_locked(stream, rows, {"action": "training_started", "improvement_cycle": IMPROVEMENT_CYCLE,
                                            "candidate": candidate_id, "cycle_sha256": cycle["cycle_sha256"],
                                            "attempt": len(attempts) + 1})


def verify_frozen(cycle_path):
    from recase.ledger import digest
    from scripts.dataset_control import audit_files
    from scripts.verify_os_isolation import verify
    path = Path(cycle_path).resolve(strict=True)
    cycle = json.loads(path.read_text())
    if cycle.get("cycle_sha256") != digest({k: v for k, v in cycle.items() if k != "cycle_sha256"}):
        raise PermissionError("Frozen cycle manifest changed")
    if cycle.get("state") != "FROZEN":
        raise PermissionError("Cycle is not FROZEN")
    for item in cycle["bound_files"].values():
        if file_digest(item["path"]) != item["sha256"]:
            raise PermissionError("Frozen input/review/exposure file changed; cycle invalidated")
    if audit_files(**cycle["audit_inputs"])["status"] != "PASS":
        raise PermissionError("Live dataset/review/exposure gate failed")
    isolation = cycle["isolation"]
    fresh = verify(isolation["service_user"], isolation["evaluator_user"], isolation["answers"],
                   isolation["protected_root"], isolation["workspace"])
    if fresh["status"] != "PASS" or fresh["answer_sha256"] != isolation["answer_sha256"]:
        raise PermissionError("Live real-answer OS isolation gate failed")
    return cycle


def compare_arms(runs):
    if set(runs) != set(ARMS):
        raise ValueError("All six A..F runs required; missing arms must remain NOT_RUN")
    baseline = runs["A"]["identity"]
    ids = baseline.get("sample_ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(sid, str) for sid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Non-empty unique sample_ids required")
    tuned_adapters = {runs[name].get("identity", {}).get("adapter_sha256") for name in ("B", "D", "F")}
    if len(tuned_adapters) != 1 or None in tuned_adapters:
        raise ValueError("B/D/F require the same verified non-empty adapter identity")
    for name, run in runs.items():
        identity = run.get("identity", {})
        if any(key not in baseline or identity.get(key) != baseline[key] for key in MATCHED_FIELDS):
            raise ValueError(f"{name}: unmatched information/model/protocol/selection conditions")
        if identity.get("arm") != ARMS[name]:
            raise ValueError(f"{name}: incorrect ablation identity")
        if not ARMS[name]["adapter"] and identity.get("adapter_sha256") is not None:
            raise ValueError(f"{name}: Base arm unexpectedly loads an adapter")
        if run.get("runtime_failures") or any(run.get("integrity_errors", {}).values()):
            raise ValueError(f"{name}: runtime/integrity failure; preserve as failed run")
        for field in ("model_calls", "prompt_tokens", "generation_tokens", "mean_latency_s", "macro_f1", "invalid_rate"):
            if field not in run:
                raise ValueError(f"{name}: cost/quality field missing: {field}")
            if type(run[field]) not in (int, float) or not math.isfinite(run[field]) or run[field] < 0:
                raise ValueError(f"{name}: invalid cost/quality value: {field}")
        if run["macro_f1"] > 1 or run["invalid_rate"] > 1 or run["model_calls"] > len(ids) * (4 if ARMS[name]["agent"] else 1):
            raise ValueError(f"{name}: quality/call budget outside frozen bounds")
    return {name: {key: run[key] for key in ("macro_f1", "invalid_rate", "mean_latency_s", "model_calls", "prompt_tokens", "generation_tokens")}
            for name, run in runs.items()}


def blocked_plan(reasons, model_identity=None):
    return {"created_at": utc_now(), "target": "this Mac, loopback only", "improvement_cycle": IMPROVEMENT_CYCLE,
            "state": "BLOCKED", "max_new_training_attempts": MAX_CANDIDATES, "new_training_attempts": 0,
            "model_identity": model_identity, "blocking_reasons": reasons,
            "arms": {name: {**config, "status": "NOT_RUN", "blocking_reasons": reasons} for name, config in ARMS.items()},
            "rules": ["Select settings on reviewed validation only; freeze before blind final use.",
                      "Same cases/public evidence/reference access/revision/quantization/decoding/output/scorer/platform.",
                      "Count failures, calls, tokens and latency. Agent arms use at most4 calls, no hidden evidence.",
                      "A..D use1 call. E/F cost differences are reported; information differences prevent pure-agent-effect claims.",
                      "No paid call, public deployment or original-document external transmission."]}
