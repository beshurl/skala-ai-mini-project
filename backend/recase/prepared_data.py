"""Read sealed public development packets; never turn automated checks into review."""
import json
import os
from collections import Counter
from pathlib import Path

from recase.dataset_control import exposure_entries, related, signature
from recase.ledger import digest, file_digest, read_ledger
from recase.paths import PROJECT_ROOT

NLI_DATASETS = ("nli_train_candidates", "nli_validation", "nli_diagnostic")
NLI_LABELS = {"entailment", "contradiction", "neutral"}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def inside(packet, name):
    path = (packet / name).resolve(strict=True)
    if not path.is_relative_to(packet) or not path.is_file():
        raise ValueError("Packet files must stay inside the sealed directory")
    return path


def load_packet(value):
    from scripts.prepared_workflow import validate_packet
    packet = validate_packet(value)
    protocol = json.loads((packet / "protocol.json").read_text())
    for name, sha in protocol["source_code_hashes"].items():
        path = (PROJECT_ROOT / name).resolve(strict=True)
        if not path.is_relative_to(PROJECT_ROOT) or file_digest(path) != sha:
            raise ValueError("Protocol-bound application code changed; a new packet version is required")
    item_path = inside(packet, "reviews/items.jsonl")
    if file_digest(item_path) != protocol["review_items_sha256"]:
        raise ValueError("Review subjects changed; a new packet version is required")
    items = rows(item_path)
    if len({i["sample_id"] for i in items}) != len(items):
        raise ValueError("Unique review sample IDs required")
    by_id = {i["sample_id"]: i for i in items}
    datasets = {}
    seen = set()
    for name, spec in protocol["datasets"].items():
        inputs_path, answers_path = (inside(packet, spec[k]) for k in ("inputs", "answers"))
        if file_digest(inputs_path) != spec["inputs_sha256"] or file_digest(answers_path) != spec["answers_sha256"]:
            raise ValueError("Predeclared dataset bytes changed")
        inputs, answers = rows(inputs_path), rows(answers_path)
        ids = [i["sample_id"] for i in inputs]
        if len(ids) != spec["count"] or len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("Dataset count/ID integrity failure")
        seen.update(ids)
        gold = {a["sample_id"]: a for a in answers}
        if len(answers) != len(gold) or set(gold) != set(ids):
            raise ValueError("Answer IDs must match all predeclared inputs")
        for inp in inputs:
            item = by_id.get(inp["sample_id"], {})
            subject = item.get("subject", {})
            if (inp.get("dataset") != name or inp.get("task") != spec["task"]
                    or subject.get("input") != inp or subject.get("answer") != gold[inp["sample_id"]]
                    or item.get("subject_sha256") != digest(subject)):
                raise ValueError("Review subject does not bind the actual input/answer")
        datasets[name] = {"inputs": inputs, "answers": gold, "spec": spec}
    if seen != set(by_id):
        raise ValueError("Review subjects must cover exactly the declared datasets")
    return packet, protocol, datasets, items


def read_reviews(path):
    path = Path(path)
    if not path.exists():
        return {}
    if path.is_symlink() or path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077:
        raise PermissionError("Human review ledger must be operator owned, mode0600 and regular")
    previous, latest = "0" * 64, {}
    for entry in rows(path):
        body = {k: v for k, v in entry.items() if k != "sha256"}
        if body.get("previous_sha256") != previous or digest(body) != entry.get("sha256"):
            raise ValueError("Invalid review ledger chain")
        previous = entry["sha256"]
        latest[entry["subject_sha256"]] = entry
    return latest


def license_hashes(item):
    return {name: file_digest(name) for name in item["subject"].get("license_files", [])}


def permitted(item, review):
    subject = item["subject"]
    return bool(review and item["subject_sha256"] == digest(subject)
        and review.get("subject_sha256") == item["subject_sha256"]
        and review.get("action") == "approve" and review.get("actor_kind") == "human_attestation"
        and isinstance(review.get("reviewer"), str) and review["reviewer"].strip()
        and review.get("reviewed_at") and review.get("note")
        and all(review.get(k) is True for k in ("privacy_checked", "labels_checked", "license_terms_checked"))
        and review.get("permissions", {}).get("processing") is True
        and (subject["requested_use"] != "training" or review.get("permissions", {}).get("training") is True)
        and (subject["rights_basis"] != "CC-BY-NC-4.0" or review.get("local_noncommercial_scope") is True)
        # Existing per-item attestations remain usable; new attestations also seal license bytes.
        and ("license_hashes" not in review or review["license_hashes"] == license_hashes(item)))


def status(value):
    packet, _, datasets, items = load_packet(value)
    reviews = read_reviews(packet / "reviews/human_reviews.jsonl")
    counts = {name: {"total": len(ds["inputs"]), "approved": 0, "rejected": 0, "pending": 0} for name, ds in datasets.items()}
    for item in items:
        review = reviews.get(item["subject_sha256"])
        state = "approved" if permitted(item, review) else "rejected" if review and review.get("action") == "reject" else "pending"
        counts[item["subject"]["input"]["dataset"]][state] += 1
    return {"datasets": counts, "human_reviews_created_by_this_command": 0}


def nli_signature(inp):
    # Shared instructions are not document-family evidence. Compare only the propositions.
    body = inp["prompt"].split("\n전제: ", 1)[-1]
    return signature({"sample_id": inp["sample_id"], "text": body, "case_family": inp.get("case_family")})


def audit_native_nli(prepared, history):
    from recase.delegated_review import load_delegation, known_history_covered, review_kind
    packet, protocol, datasets, items = load_packet(prepared)
    reviews = read_reviews(packet / "reviews/human_reviews.jsonl")
    delegation = load_delegation(packet, items)
    issues = []
    def issue(code, sid=None):
        issues.append({"code": code, **({"sample_id": sid} if sid else {})})
    entries = exposure_entries(history)
    coverage = [e["payload"] for e in read_ledger(history) if e["payload"].get("kind") == "history_coverage"]
    if not (coverage and coverage[-1].get("exposures_sha256") == digest(entries)
            and coverage[-1].get("actor_kind") == "human_attestation") and not known_history_covered(delegation, entries):
        issue("EXPOSURE_HISTORY_NOT_ATTESTED_COMPLETE")
    attempts = PROJECT_ROOT / "runtime/training-attempts.jsonl"
    if attempts.exists():
        for entry in read_ledger(attempts):
            event = entry["payload"]
            entries.extend({"purpose": "training", "signature": s} for s in event.get("training_exposure_signatures", []))
    signatures, training = [], []
    for name in NLI_DATASETS:
        ds = datasets[name]
        labels = set()
        for inp in ds["inputs"]:
            sid = inp["sample_id"]
            target = ds["answers"][sid]["target"]
            if set(target) != {"label"} or target["label"] not in NLI_LABELS or not inp.get("case_family"):
                issue("INVALID_NATIVE_NLI_TARGET_OR_FAMILY", sid)
            labels.add(target.get("label"))
            if name == "nli_train_candidates" and inp.get("upstream_split") != "upstream_train":
                issue("TRAINING_MUST_USE_UPSTREAM_TRAIN", sid)
            item = next(i for i in items if i["sample_id"] == sid)
            expected_use = "training" if name == "nli_train_candidates" else "evaluation"
            if item["subject"]["requested_use"] != expected_use:
                issue("PURPOSE_MISMATCH", sid)
            if name != "nli_diagnostic" and not review_kind(item, reviews.get(item["subject_sha256"]), delegation):
                issue("HUMAN_REVIEW_OR_PURPOSE_APPROVAL_REQUIRED", sid)
            sig = nli_signature(inp)
            for old_name, old in signatures:
                reasons = related(sig, old)
                if reasons and (old_name != name or set(reasons) - {"case_family"}):
                    issue("CROSS_SPLIT_OR_WITHIN_SPLIT_DUPLICATE", sid)
            if name != "nli_train_candidates" and any(e["purpose"] == "training" and related(sig, e["signature"]) for e in entries):
                issue("PRIOR_TRAINING_EXPOSURE", sid)
            signatures.append((name, sig))
            if name == "nli_train_candidates":
                training.append(sig)
        if labels != NLI_LABELS:
            issue("ALL_THREE_LABELS_REQUIRED:" + name)
    return {"kind": "prepared-native-nli-v1", "status": "PASS" if not issues else "BLOCKED",
            "issue_counts": dict(Counter(i["code"] for i in issues)), "issues": issues,
            "counts": {name: len(datasets[name]["inputs"]) for name in NLI_DATASETS},
            "review_policy": "delegated_public_nli" if delegation else "human_attestation_only",
            "blind_final_eligible": False,
            "external_and_pretraining_exposure": "UNKNOWN",
            "training_exposure_signatures": training,
            "scope": "Public development train/validation only; diagnostic answers never enter training files"}


def verify_native_isolation(path, packet):
    """Re-probe each real answer even when the model server has been stopped."""
    return [verify_dataset_isolation(path, packet, name) for name in NLI_DATASETS]


def verify_dataset_isolation(path, packet, dataset):
    from scripts.verify_os_isolation import verify
    report = json.loads(Path(path).read_text())
    if not isinstance(report, dict) or report.get("status") != "PASS":
        raise PermissionError("OS isolation application has not passed")
    evidence = report["answers"] if isinstance(report.get("answers"), list) else [report]
    if any(not isinstance(row, dict) for row in evidence):
        raise ValueError("Valid per-answer OS evidence required")
    _, protocol, _, _ = load_packet(packet)
    expected = protocol["datasets"][dataset]["answers_sha256"]
    candidates = [r for r in evidence if r.get("answer_sha256") == expected]
    if (len(candidates) != 1 or candidates[0].get("status") != "PASS"
            or candidates[0].get("checks", {}).get("running_service_uid_matches") is not True):
        raise PermissionError("Real running-service identity and the actual answer must be bound")
    old = candidates[0]
    fresh = verify(old["service_user"], old["evaluator_user"], old["answers"], old["protected_root"], PROJECT_ROOT)
    if fresh["status"] != "PASS" or fresh["answer_sha256"] != expected:
        if (fresh.get("service_probe", {}).get("probe_executed") is False
                or fresh.get("evaluator_probe", {}).get("probe_executed") is False):
            raise PermissionError("ACCOUNT_SWITCH_AUTH_REQUIRED: refresh sudo authentication in the same local terminal; no model loaded")
        raise PermissionError("Live real-answer OS isolation gate failed")
    return fresh
