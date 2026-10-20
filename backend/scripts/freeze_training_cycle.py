"""Freeze verified data/model/config inputs. A boolean approval.json is not accepted."""
import argparse
import json
import os
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.dataset_control import file_identity
from recase.experiments import IMPROVEMENT_CYCLE, candidate_configs
from recase.ledger import digest, utc_now
from recase.model import MODEL_ID, SYSTEM, resolve_model
from recase.paths import BACKEND_ROOT, PROJECT_ROOT
from scripts.dataset_control import audit_files, load_rows, write_new
from scripts.verify_os_isolation import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("candidates", "history", "reviews", "configs", "protocol", "isolation", "out"):
        p.add_argument("--" + key, required=True)
    args = p.parse_args()
    configs = candidate_configs(json.loads(Path(args.configs).read_text()))
    result = audit_files(args.candidates, args.history, args.reviews)
    if result["status"] != "PASS":
        p.exit(2, "DATA_GATE_BLOCKED: " + json.dumps(result["issue_counts"]) + "\n")
    isolation = json.loads(Path(args.isolation).read_text())
    fresh = verify(isolation["service_user"], isolation["evaluator_user"], isolation["answers"],
                   isolation["protected_root"], PROJECT_ROOT)
    if fresh["status"] != "PASS" or fresh["answer_sha256"] != isolation["answer_sha256"]:
        p.exit(2, "OS_ISOLATION_BLOCKED\n")
    rows = load_rows(args.candidates)
    if {r["split"] for r in rows} != {"train", "validation"}:
        p.exit(2, "Only reviewed train+validation rows belong in the training bundle; final answers stay separate\n")
    for split in ("train", "validation"):
        if {r["label"] for r in rows if r["split"] == split} != {"일치", "모순", "추가확인필요"}:
            p.exit(2, "Each split requires all3 labels; sample adequacy still needs human review\n")
    model = resolve_model()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model), local_files_only=True, trust_remote_code=False)
    converted, lengths = {"train": [], "validation": []}, []
    for row in rows:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": row["answer"]}]
        length = len(tokenizer.apply_chat_template(messages, add_generation_prompt=False, return_dict=False))
        if length > 768:
            p.exit(2, "TOKEN_LIMIT: quarantine/redesign instead of truncating " + row["sample_id"] + "\n")
        lengths.append(length)
        converted[row["split"]].append({"messages": messages})
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    for split, filename in (("train", "train.jsonl"), ("validation", "valid.jsonl")):
        fd = os.open(out / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            for row in converted[split]:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    bound = {key: file_identity(getattr(args, key)) for key in ("candidates", "history", "reviews", "configs", "protocol", "isolation")}
    bound.update({filename: file_identity(out / filename) for filename in ("train.jsonl", "valid.jsonl")})
    for filename in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        bound[filename] = file_identity(model / filename)
    for path in model.glob("*.safetensors"):
        bound[path.name] = file_identity(path)
    project = BACKEND_ROOT
    for filename in ("training/train_local.py", "recase/dataset_control.py", "recase/experiments.py",
                     "recase/paths.py", "scripts/freeze_training_cycle.py", "scripts/verify_os_isolation.py", "requirements-lock-macos-arm64.txt"):
        bound[filename] = file_identity(project / filename)
    cycle = {"state": "FROZEN", "frozen_at": utc_now(), "improvement_cycle": IMPROVEMENT_CYCLE,
             "candidates": configs, "max_attempts": 3, "data": str(out), "model": str(model),
             "model_id": MODEL_ID, "revision": model.name, "platform": platform.platform(),
             "bound_files": bound, "token_max": max(lengths), "training_timeout_seconds": 1800,
             "audit_inputs": {key: str(Path(getattr(args, key)).resolve()) for key in ("candidates", "history", "reviews")},
             "isolation": {**fresh, "workspace": str(PROJECT_ROOT)}}
    cycle["cycle_sha256"] = digest(cycle)
    write_new(out / "cycle.json", cycle)
    print(json.dumps({"state": "FROZEN", "path": str(out / "cycle.json"), "training_executed": False}))


if __name__ == "__main__":
    main()
