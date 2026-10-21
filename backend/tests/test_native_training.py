"""Temporary UNIT_TEST_FIXTURE attestations only; no real reviews or training."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from recase import native_training, prepared_data
from recase.experiments import reserve_candidate, verify_frozen
from recase.ledger import append_record, digest, file_digest, read_ledger
from scripts import prepared_workflow, review_prepared


def write(path, value, jsonl=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in value) if jsonl else json.dumps(value))
    path.chmod(0o600)


def fixture_packet(tmp_path, monkeypatch, approve=True, duplicate=False):
    monkeypatch.setattr(prepared_data, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prepared_workflow, "PROJECT", tmp_path)
    packet = tmp_path / "outputs/runs/UNIT_TEST_FIXTURE/prepared"
    packet.mkdir(parents=True)
    license_file = packet / "LICENSE-FIXTURE"
    license_file.write_text("UNIT_TEST_FIXTURE, not a real license")
    protocol = {"datasets": {}, "source_code_hashes": {}, "model": "mlx-community/Qwen3-4B-4bit", "revision": "UNIT_TEST_FIXTURE"}
    items = []
    for name in prepared_data.NLI_DATASETS:
        inputs, answers = [], []
        for label in sorted(prepared_data.NLI_LABELS):
            sid = name + "-" + label
            inp = {"sample_id": sid, "task": "nli", "dataset": name,
                   "prompt": "\n전제: " + digest(sid), "case_family": sid,
                   "upstream_split": "upstream_train" if name == "nli_train_candidates" else "upstream_development"}
            if duplicate and name == "nli_validation" and label == "neutral":
                inp["case_family"] = "nli_train_candidates-neutral"
            answer = {"sample_id": sid, "target": {"label": label}}
            subject = {"input": inp, "answer": answer, "rights_basis": "UNIT_TEST_FIXTURE",
                       "license_files": [str(license_file)], "requested_use": "training" if name == "nli_train_candidates" else "evaluation"}
            items.append({"sample_id": sid, "subject": subject, "subject_sha256": digest(subject)})
            inputs.append(inp)
            answers.append(answer)
        spec = {"task": "nli", "count": 3, "inputs": "inputs/" + name + ".jsonl", "answers": "answers/" + name + ".jsonl"}
        for key, values in (("inputs", inputs), ("answers", answers)):
            write(packet / spec[key], values, True)
            spec[key + "_sha256"] = file_digest(packet / spec[key])
        protocol["datasets"][name] = spec
    write(packet / "reviews/items.jsonl", items, True)
    protocol["review_items_sha256"] = file_digest(packet / "reviews/items.jsonl")
    write(packet / "protocol.json", protocol)
    write(packet / "selection_policy.json", {"validation_dataset": "nli_validation", "maximum_new_candidates": 3})
    write(packet / "tool_manifest.json", {name: file_digest(packet / name) for name in ("protocol.json", "selection_policy.json")})
    if approve:
        for item in items:
            if item["subject"]["input"]["dataset"] != "nli_diagnostic":
                review_prepared.append_review(packet / "reviews/human_reviews.jsonl", attestation(item))
    history = tmp_path / "history.jsonl"
    append_record(history, {"kind": "history_coverage", "actor_kind": "human_attestation", "exposures_sha256": digest([]), "scope": "UNIT_TEST_FIXTURE"})
    return packet, history, items


def attestation(item):
    return {"subject_sha256": item["subject_sha256"], "sample_id": item["sample_id"], "action": "approve",
            "actor_kind": "human_attestation", "reviewer": "UNIT_TEST_FIXTURE", "reviewed_at": "UNIT_TEST_ONLY",
            "note": "UNIT_TEST_ONLY", "privacy_checked": True, "labels_checked": True, "license_terms_checked": True,
            "permissions": {"processing": True, "training": item["subject"]["requested_use"] == "training"},
            "license_hashes": prepared_data.license_hashes(item)}


def test_native_contract_reviews_and_known_exposure_gate(tmp_path, monkeypatch):
    packet, history, items = fixture_packet(tmp_path, monkeypatch)
    assert prepared_data.audit_native_nli(packet, history)["status"] == "PASS"
    # Evaluation approval does not permit training; later rejection revokes approval.
    event = attestation(items[0])
    event["permissions"]["training"] = False
    assert not prepared_data.permitted(items[0], event)
    review_prepared.append_review(packet / "reviews/human_reviews.jsonl", {**attestation(items[0]), "action": "reject"})
    report = prepared_data.audit_native_nli(packet, history)
    assert report["issue_counts"]["HUMAN_REVIEW_OR_PURPOSE_APPROVAL_REQUIRED"] == 1
    assert prepared_data.status(packet)["datasets"]["nli_train_candidates"]["rejected"] == 1


def test_cross_split_family_and_prior_training_are_rejected(tmp_path, monkeypatch):
    packet, history, items = fixture_packet(tmp_path, monkeypatch, duplicate=True)
    report = prepared_data.audit_native_nli(packet, history)
    assert report["issue_counts"]["CROSS_SPLIT_OR_WITHIN_SPLIT_DUPLICATE"]
    inp = next(i["subject"]["input"] for i in items if i["subject"]["input"]["dataset"] == "nli_validation")
    append_record(history, {"kind": "exposure", "purpose": "training", "signature": prepared_data.nli_signature(inp)})
    report = prepared_data.audit_native_nli(packet, history)
    assert report["issue_counts"]["PRIOR_TRAINING_EXPOSURE"]
    assert report["issue_counts"]["EXPOSURE_HISTORY_NOT_ATTESTED_COMPLETE"]


def test_changed_input_and_license_cannot_reuse_approval(tmp_path, monkeypatch):
    packet, _, items = fixture_packet(tmp_path, monkeypatch)
    review = attestation(items[0])
    Path(items[0]["subject"]["license_files"][0]).write_text("CHANGED_UNIT_TEST_LICENSE")
    assert not prepared_data.permitted(items[0], review)
    with (packet / "inputs/nli_validation.jsonl").open("a") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="bytes changed"):
        prepared_data.load_packet(packet)


def test_no_reviews_cannot_create_bundle_or_reach_tokenizer_os_or_training(tmp_path, monkeypatch):
    packet, history, _ = fixture_packet(tmp_path, monkeypatch, approve=False)
    configs = tmp_path / "configs.json"
    write(configs, [{"id": "fixture", "iters": 1, "rank": 8, "layers": 8, "sequence_length": 768, "learning_rate": 1e-4}])
    def forbidden(*args, **kwargs):
        raise AssertionError("Must not reach OS/model conversion before real review gate")
    monkeypatch.setattr(native_training, "verify_native_isolation", forbidden)
    monkeypatch.setattr(native_training, "resolve_model", forbidden)
    out = tmp_path / "must-not-exist"
    with pytest.raises(PermissionError, match="DATA_GATE_BLOCKED"):
        native_training.freeze_native(packet, history, configs, packet / "protocol.json", tmp_path / "absent-isolation", out)
    assert not out.exists() and not (tmp_path / "runtime/training-attempts.jsonl").exists()


def test_review_queue_covers_all_items_and_rejection_is_resumable(tmp_path, monkeypatch):
    packet, _, items = fixture_packet(tmp_path, monkeypatch, approve=False)
    latest = {items[0]["subject_sha256"]: {"action": "reject"}}
    priorities = [{"subject_sha256": items[2]["subject_sha256"], "flags": ["FIXTURE_FLAG"]}]
    pending = review_prepared.pending_items(items, latest, "nli_train_candidates", priorities=priorities)
    assert len(pending) == 2 and pending[0] == items[2]
    assert review_prepared.pending_items(items, latest, "nli_train_candidates", items[0]["sample_id"]) == [items[0]]
    result = subprocess.run([sys.executable, str(Path(review_prepared.__file__)), "review", "--prepared", str(packet)],
                            input="yes\n" * 20, text=True, capture_output=True)
    assert result.returncode != 0 and "PermissionError" in result.stderr
    assert not (packet / "reviews/human_reviews.jsonl").exists()


class TokenizerFixture:
    def apply_chat_template(self, messages, tokenize=True, **kwargs):
        if not tokenize:
            return "FIXTURE_PREFIX" + (messages[-1]["content"] if messages[-1]["role"] == "assistant" else "")
        return [1] * 20


def test_native_freeze_reuses_global_budget_and_excludes_diagnostic_answers(tmp_path, monkeypatch):
    packet, history, items = fixture_packet(tmp_path, monkeypatch)
    model = tmp_path / "UNIT_TEST_FIXTURE"
    model.mkdir()
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"):
        (model / name).write_text("UNIT_TEST_FIXTURE_NOT_MODEL_WEIGHTS")
    monkeypatch.setattr(native_training, "resolve_model", lambda: model)
    monkeypatch.setattr(native_training, "verify_native_isolation", lambda *args: ["UNIT_TEST_ONLY_NOT_REAL_OS_PROOF"])
    import transformers
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **k: TokenizerFixture())
    configs = tmp_path / "configs.json"
    write(configs, [{"id": "fixture", "iters": 1, "rank": 8, "layers": 8, "sequence_length": 768, "learning_rate": 1e-4}])
    isolation = tmp_path / "isolation.json"
    write(isolation, {"UNIT_TEST_FIXTURE": True})
    out = tmp_path / "frozen"
    cycle = native_training.freeze_native(packet, history, configs, packet / "protocol.json", isolation, out)
    assert cycle["audit_kind"] == "prepared_native_nli_v1" and cycle["max_attempts"] == 3
    assert len(prepared_data.rows(out / "train.jsonl")) == len(prepared_data.rows(out / "valid.jsonl")) == 3
    diagnostic_prompts = [i["subject"]["input"]["prompt"] for i in items if i["subject"]["input"]["dataset"] == "nli_diagnostic"]
    messages = [row["messages"][1]["content"] for name in ("train.jsonl", "valid.jsonl") for row in prepared_data.rows(out / name)]
    assert not set(diagnostic_prompts).intersection(messages)
    assert (out / "train.jsonl").stat().st_mode & 0o077 == 0
    ledger = tmp_path / "runtime/training-attempts.jsonl"
    reserve_candidate(ledger, cycle, "fixture")
    assert len(read_ledger(ledger)[0]["payload"]["training_exposure_signatures"]) == 3
    monkeypatch.setattr(prepared_data, "verify_native_isolation", lambda *args: [])
    assert verify_frozen(out / "cycle.json")["cycle_sha256"] == cycle["cycle_sha256"]
    review_prepared.append_review(packet / "reviews/human_reviews.jsonl", {**attestation(items[0]), "action": "reject"})
    with pytest.raises(PermissionError, match="invalidated"):
        verify_frozen(out / "cycle.json")


def test_native_converter_refuses_truncation_and_template_drift():
    class TooLong(TokenizerFixture):
        def apply_chat_template(self, messages, tokenize=True, **kwargs):
            return [1] * 769 if tokenize else super().apply_chat_template(messages, tokenize=tokenize, **kwargs)
    with pytest.raises(PermissionError, match="TOKEN_LIMIT"):
        native_training.convert_row({"prompt": "UNIT_TEST"}, {"target": {"label": "neutral"}}, TooLong())
    class Drift(TokenizerFixture):
        def apply_chat_template(self, messages, **kwargs):
            return "WRONG" if len(messages) == 3 else "PREFIX"
    with pytest.raises(ValueError, match="prefix"):
        native_training.convert_row({"prompt": "UNIT_TEST"}, {"target": {"label": "neutral"}}, Drift())
