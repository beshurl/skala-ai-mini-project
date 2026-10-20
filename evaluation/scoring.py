"""Strict legacy contract, fixed label set, and gold-denominator scoring."""
import json
import math
import re
from collections import Counter

LABELS = ("일치", "모순", "추가확인필요")
PROTOCOL = "recase-eval-v2"


def parse_response(text, allowed_ids, recover=False):
    if not isinstance(text, str):
        return None, "non_text"
    if recover:
        text = re.sub(r"^\s*<think>.*?</think>\s*", "", text, count=1, flags=re.S)
        fenced = re.fullmatch(r"\s*```(?:json)?\s*\n?(.*?)\n?```\s*", text, re.S)
        if fenced:
            text = fenced[1]
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None, "json_syntax"
    if not isinstance(obj, dict) or obj.get("label") not in LABELS:
        return None, "label"
    if not isinstance(obj.get("reason"), str) or not obj["reason"].strip():
        return None, "reason"
    ids = obj.get("evidence_ids")
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        return None, "evidence_ids"
    if len(set(ids)) != len(ids) or not set(ids).issubset(allowed_ids):
        return None, "inaccessible_evidence"
    if obj["label"] != "추가확인필요" and not ids:
        return None, "missing_citation"
    return obj, None


def allowed_evidence(example):
    if "evidence" in example:
        return {e["id"] for e in example["evidence"] if e.get("public", True)}
    return set(re.findall(r"(?m)^(E[\w-]+):", example["prompt"]))


def percentile(values, q):
    if not values:
        return None
    v = sorted(values)
    p = (len(v) - 1) * q
    lo = int(p)
    return v[lo] + (v[min(lo + 1, len(v) - 1)] - v[lo]) * (p - lo)


def score(examples, predictions):
    if not examples or len({e["case_id"] for e in examples}) != len(examples):
        raise ValueError("Empty dataset or duplicate gold IDs")
    if any(e["label"] not in LABELS for e in examples):
        raise ValueError("Unknown gold label")
    counts = Counter(p.get("case_id") for p in predictions)
    known = {e["case_id"] for e in examples}
    unexpected = sorted(str(k) for k in counts if k not in known)
    by_id = {p.get("case_id"): p for p in predictions}
    rows = []
    for e in examples:
        p = by_id.get(e["case_id"], {})
        raw = p.get("response", p.get("answer", ""))
        obj, err = parse_response(raw, allowed_evidence(e))
        recovered, recovery_error = parse_response(raw, allowed_evidence(e), recover=True)
        if counts[e["case_id"]] != 1:
            obj = recovered = None
            err = recovery_error = "missing_prediction" if not counts[e["case_id"]] else "duplicate_prediction"
        rows.append({**p, "case_id": e["case_id"], "gold": e["label"],
                     "pred": obj["label"] if obj else "invalid", "error": err,
                     "recovered_pred": recovered["label"] if recovered else "invalid",
                     "recovery_error": recovery_error})
    n = len(rows)
    report = {}
    for label in LABELS:
        tp = sum(r["gold"] == label and r["pred"] == label for r in rows)
        fp = sum(r["gold"] != label and r["pred"] == label for r in rows)
        fn = sum(r["gold"] == label and r["pred"] != label for r in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        report[label] = {"precision": precision, "recall": recall,
                         "f1-score": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                         "support": sum(r["gold"] == label for r in rows)}
    latencies = [r["seconds"] for r in rows if isinstance(r.get("seconds"), (int, float)) and math.isfinite(r["seconds"]) and r["seconds"] >= 0]
    metrics = {"protocol": PROTOCOL, "count": n,
        "accuracy": sum(r["gold"] == r["pred"] for r in rows) / n,
        "macro_f1": sum(v["f1-score"] for v in report.values()) / len(LABELS),
        "invalid_rate": sum(r["pred"] == "invalid" for r in rows) / n,
        "raw_structured_success_rate": sum(r["error"] is None for r in rows) / n,
        "recovered_structured_success_rate": sum(r["recovery_error"] is None for r in rows) / n,
        "recovered_accuracy": sum(r["gold"] == r["recovered_pred"] for r in rows) / n,
        "classification_report": report,
        "mean_latency_s": sum(latencies) / len(latencies) if latencies else None,
        "latency_p50_s": percentile(latencies, .5), "latency_p95_s": percentile(latencies, .95),
        "latency_measured_count": len(latencies),
        "integrity_errors": {"unexpected_ids": unexpected, "duplicate_ids": sorted(str(k) for k, v in counts.items() if v > 1)},
        "semantic_citation_correctness": "NOT_MEASURED", "hypothesis_update_accuracy": "NOT_MEASURED"}
    return metrics, rows
