"""Native NLI integration with the existing frozen cycle and global attempt ledger."""
import json
import os
import platform
from pathlib import Path

from recase.dataset_control import file_identity
from recase.experiments import IMPROVEMENT_CYCLE, candidate_configs
from recase.ledger import digest, file_digest, utc_now
from recase.model import MODEL_ID, SYSTEM, resolve_model
from recase.paths import BACKEND_ROOT
from recase.prepared_data import audit_native_nli, load_packet, verify_native_isolation
from scripts.dataset_control import write_new


def finalize_native_adapter(output, cycle):
    """Canonicalize only a newly produced adapter's base identity, preserving bytes."""
    if cycle.get("audit_kind") != "prepared_native_nli_v1":
        raise ValueError("Native cycle required for adapter identity normalization")
    out = Path(output)
    config = out / "adapter/adapter_config.json"
    weights = out / "adapter/adapters.safetensors"
    if config.is_symlink() or weights.is_symlink() or not weights.is_file():
        raise ValueError("Regular newly produced native adapter files required")
    original = config.read_bytes()
    metadata = json.loads(original)
    if metadata.get("model") not in (cycle["model"], cycle["model_id"]):
        raise ValueError("Generated adapter base differs from the actual frozen model")
    before = file_digest(weights)
    preserved = out / "adapter_config.generated.json"
    fd = os.open(preserved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(original)
    metadata.update(model=cycle["model_id"], model_revision=cycle["revision"], training_model_path=cycle["model"])
    temporary = out / "adapter/adapter_config.canonical.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(config)
    if file_digest(weights) != before:
        raise ValueError("Adapter weight bytes changed unexpectedly")
    write_new(out / "adapter_identity.json", {"model": cycle["model_id"], "revision": cycle["revision"],
        "generated_config_sha256": file_digest(preserved), "canonical_config_sha256": file_digest(config),
        "adapter_sha256": before, "weight_bytes_preserved": True, "cycle_sha256": cycle["cycle_sha256"]})


def convert_row(inp, answer, tokenizer):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": inp["prompt"]},
                {"role": "assistant", "content": json.dumps(answer["target"], ensure_ascii=False)}]
    # Match the installed mlx_lm ChatDataset, including its default training mask prefix.
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    if not full.startswith(prefix):
        raise ValueError("Native NLI training/inference chat templates do not share a prefix")
    tokens = tokenizer.apply_chat_template(messages, add_generation_prompt=False, return_dict=False)
    if not isinstance(tokens, list) or not all(type(n) is int for n in tokens) or len(tokens) > 768:
        raise PermissionError("TOKEN_LIMIT_OR_ENCODING: quarantine/redesign instead of truncation")
    return {"messages": messages}, len(tokens)


def freeze_native(prepared, history, configs_path, protocol_path, isolation_path, destination):
    packet, protocol, datasets, items = load_packet(prepared)
    raw_configs = json.loads(Path(configs_path).read_text())
    configs = candidate_configs(raw_configs["candidates"] if isinstance(raw_configs, dict) else raw_configs)
    audit = audit_native_nli(packet, history)
    if audit["status"] != "PASS":
        raise PermissionError("DATA_GATE_BLOCKED: " + json.dumps(audit["issue_counts"]))
    verified = verify_native_isolation(isolation_path, packet)
    selection = json.loads((packet / "selection_policy.json").read_text())
    if selection["validation_dataset"] != "nli_validation" or selection["maximum_new_candidates"] != 3:
        raise ValueError("Predeclared native NLI validation selection policy required")
    model = resolve_model()
    if protocol["model"] != MODEL_ID or protocol["revision"] != model.name:
        raise ValueError("Model identity differs from the sealed packet")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model), local_files_only=True, trust_remote_code=False)
    converted, lengths = {}, []
    for name, filename in (("nli_train_candidates", "train.jsonl"), ("nli_validation", "valid.jsonl")):
        ds = datasets[name]
        converted[filename] = []
        for inp in ds["inputs"]:
            row, size = convert_row(inp, ds["answers"][inp["sample_id"]], tokenizer)
            converted[filename].append(row)
            lengths.append(size)
    out = Path(destination).resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    for filename, examples in converted.items():
        fd = os.open(out / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in examples)
    bound = {name: file_identity(path) for name, path in {
        "history": history, "reviews": packet / "reviews/human_reviews.jsonl", "configs": configs_path,
        "protocol": protocol_path, "packet_protocol": packet / "protocol.json", "tool_manifest": packet / "tool_manifest.json",
        "selection_policy": packet / "selection_policy.json", "review_subjects": packet / "reviews/items.jsonl",
        "isolation": isolation_path, **{f: out / f for f in converted}}.items()}
    from recase.delegated_review import GRANT, REVIEWS, COVERAGE
    if GRANT in json.loads((packet / "tool_manifest.json").read_text()):
        for name in (GRANT, REVIEWS, COVERAGE):
            bound["delegation:" + name] = file_identity(packet / name)
    for name in ("nli_train_candidates", "nli_validation", "nli_diagnostic"):
        for key in ("inputs", "answers"):
            bound[name + ":" + key] = file_identity(packet / protocol["datasets"][name][key])
    for item in items:
        for path in item["subject"].get("license_files", []):
            bound["license:" + path] = file_identity(path)
    for path in [model / name for name in ("config.json", "tokenizer.json", "tokenizer_config.json")] + list(model.glob("*.safetensors")):
        bound["model:" + path.name] = file_identity(path)
    for name in ("training/train_local.py", "recase/native_training.py", "recase/prepared_data.py", "recase/delegated_review.py", "recase/experiments.py",
                 "recase/ledger.py", "recase/dataset_control.py", "recase/model.py", "recase/paths.py",
                 "scripts/prepared_workflow.py", "scripts/freeze_training_cycle.py", "scripts/verify_os_isolation.py",
                 "evaluation/evaluate_prepared.py",
                 "requirements-lock-macos-arm64.txt"):
        bound["code:" + name] = file_identity(BACKEND_ROOT / name)
    cycle = {"state": "FROZEN", "frozen_at": utc_now(), "improvement_cycle": IMPROVEMENT_CYCLE,
             "audit_kind": "prepared_native_nli_v1", "candidates": configs, "max_attempts": 3,
             "data": str(out), "model": str(model), "model_id": MODEL_ID, "revision": model.name,
             "platform": platform.platform(), "token_max": max(lengths), "training_timeout_seconds": 1800,
             "bound_files": bound, "audit_inputs": {"prepared": str(packet), "history": str(Path(history).resolve())},
             "native_isolation_path": str(Path(isolation_path).resolve()), "verified_real_answers": verified,
             "training_exposure_signatures": audit["training_exposure_signatures"],
             "output_contract": {"label": "entailment|contradiction|neutral"}, "selection_policy": selection,
             "scope": "Public development NLI only; no diagnostic/final answers in train/valid files"}
    cycle["cycle_sha256"] = digest(cycle)
    write_new(out / "cycle.json", cycle)
    return cycle


def verify_native_cycle(cycle):
    audit = audit_native_nli(**cycle["audit_inputs"])
    if audit["status"] != "PASS":
        raise PermissionError("Live native NLI dataset/review/exposure gate failed")
    verify_native_isolation(cycle["native_isolation_path"], cycle["audit_inputs"]["prepared"])
