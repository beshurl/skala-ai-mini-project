"""Reject comparisons without matching model, dataset and generation identity."""
import argparse
import json
from pathlib import Path

FIELDS = ("model", "revision", "config_sha256", "tokenizer_sha256", "quantization", "prompt_sha256", "prompt_version", "generation", "protocol", "dataset_sha256", "sample_ids", "platform")


def compare(a, b):
    left, right = a.get("identity", {}), b.get("identity", {})
    problems = [k for k in FIELDS if k not in left or k not in right or left[k] != right[k]]
    if problems:
        raise ValueError("UNVERIFIED comparison conditions: " + ", ".join(problems))
    if a.get("runtime_failures") or b.get("runtime_failures"):
        raise ValueError("Runtime failures prevent a valid model comparison")
    if any(any(run.get("integrity_errors", {}).values()) for run in (a, b)):
        raise ValueError("Prediction integrity errors")
    return {k: {"base": a[k], "tuned": b[k], "delta": b[k] - a[k]} for k in ("accuracy", "macro_f1", "invalid_rate", "mean_latency_s")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("tuned")
    a = p.parse_args()
    try:
        result = compare(*[json.loads(Path(x).read_text()) for x in (a.base, a.tuned)])
    except ValueError as err:
        p.exit(2, str(err) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
