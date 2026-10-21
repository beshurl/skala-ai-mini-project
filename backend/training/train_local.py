"""Train one predeclared, reviewed candidate. Every launched attempt counts."""
import argparse
import fcntl
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.experiments import reserve_candidate, verify_frozen
from recase.ledger import append_record, utc_now
from recase.paths import PROJECT_ROOT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycle", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    cycle = verify_frozen(args.cycle)
    candidates = {c["id"]: c for c in cycle["candidates"]}
    if args.candidate not in candidates:
        p.error("Candidate was not declared at freeze time")
    config = candidates[args.candidate]
    root = PROJECT_ROOT
    runtime = root / "runtime"
    runtime.mkdir(exist_ok=True, mode=0o700)
    ledger = runtime / "training-attempts.jsonl"
    with (runtime / "model.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            p.exit(2, "MODEL_BUSY: stop the model server before training\n")
        out = Path(args.out).resolve()
        if out.exists():
            p.error("Existing output refused")
        # One locked ledger shared across freeze folders. Failures also count.
        reservation = reserve_candidate(ledger, cycle, args.candidate)
        out.mkdir(parents=True, exist_ok=False, mode=0o700)
        config_path = out / "training-config.json"
        config_path.write_text(json.dumps({"lora_parameters": {"rank": config["rank"], "scale": 20.0, "dropout": 0.0},
                                           "seed": 0, "report_to": ""}, indent=2))
        command = [sys.executable, "-m", "mlx_lm", "lora", "--model", cycle["model"], "--train", "--data", cycle["data"],
                   "--config", str(config_path),
                   "--batch-size", "1", "--num-layers", str(config["layers"]), "--iters", str(config["iters"]),
                   "--learning-rate", str(config["learning_rate"]), "--max-seq-length", str(config["sequence_length"]),
                   "--grad-checkpoint", "--mask-prompt", "--adapter-path", str(out / "adapter"),
                   "--save-every", str(config["iters"]), "--steps-per-eval", str(config["iters"]), "--val-batches", "-1"]
        plan = {"command": command, "started_at": utc_now(), "reservation": reservation["sha256"],
                "max_seconds": 1800, "memory_stop": "operator interruption on system memory pressure", "cycle": cycle["cycle_sha256"]}
        (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
        exit_code, status = 1, "FAILED"
        try:
            with (out / "training.log").open("x") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            if result.returncode == 0 and cycle.get("audit_kind") == "prepared_native_nli_v1":
                from recase.native_training import finalize_native_adapter
                finalize_native_adapter(out, cycle)
            exit_code = result.returncode
            status = "COMPLETED" if exit_code == 0 else "FAILED"
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
        except KeyboardInterrupt:
            status = "INTERRUPTED"
            exit_code = 130
        finally:
            append_record(ledger, {"action": "training_finished", "reservation": reservation["sha256"],
                                   "candidate": args.candidate, "status": status, "exit_code": exit_code,
                                   "finished_at": utc_now(), "output": str(out)})
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
