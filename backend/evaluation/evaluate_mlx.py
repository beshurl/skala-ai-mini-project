"""Evaluate cached Qwen3-4B and preserve complete run identity and failures."""
import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.paths import PROJECT_ROOT
from evaluation.scoring import PROTOCOL, score
from recase.model import LocalModel, MODEL_ID


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL_ID)
    p.add_argument("--adapter")
    p.add_argument("--test", default=str(PROJECT_ROOT / "data/processed/test.jsonl"))
    p.add_argument("--out")
    p.add_argument("--limit", type=int, default=54)
    a = p.parse_args()
    if a.limit < 1:
        p.error("--limit must be positive")
    source = Path(a.test)
    examples = [json.loads(x) for x in source.read_text().splitlines() if x.strip()][:a.limit]
    score(examples, [])
    out = Path(a.out) if a.out else (PROJECT_ROOT / "outputs/runs") / (datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + ("-ft" if a.adapter else "-base"))
    out.mkdir(parents=True, exist_ok=False)
    model = LocalModel(a.model, a.adapter)
    model.load()
    identity = {**model.info, "protocol": PROTOCOL,
                "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "sample_ids": [e["case_id"] for e in examples],
                "evaluation_use": "development_exposed", "platform": platform.platform(),
                "started_at": datetime.now().astimezone().isoformat()}
    (out / "manifest.json").write_text(json.dumps(identity, ensure_ascii=False, indent=2))
    rows = []
    with (out / "raw_predictions.jsonl").open("x") as f:
        for i, ex in enumerate(examples):
            try:
                row = {"case_id": ex["case_id"], **model.infer(ex["prompt"])}
            except Exception as err:
                row = {"case_id": ex["case_id"], "response": "", "runtime_error": type(err).__name__}
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f'{i+1}/{len(examples)} {ex["case_id"]}', flush=True)
    metrics, scored = score(examples, rows)
    metrics["identity"] = identity
    metrics["model_calls"] = len(rows)
    metrics["prompt_tokens"] = sum(r.get("prompt_tokens", 0) for r in rows)
    metrics["generation_tokens"] = sum(r.get("generation_tokens", 0) for r in rows)
    metrics["peak_allocated_memory_gb"] = max((r.get("peak_memory_gb", 0) for r in rows), default=0)
    metrics["runtime_failures"] = sum("runtime_error" in r for r in rows)
    (out / "predictions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in scored))
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in metrics.items() if k not in ("identity", "classification_report")}, ensure_ascii=False, indent=2), flush=True)
    if metrics["runtime_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
