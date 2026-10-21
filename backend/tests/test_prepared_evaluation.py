"""No real model, privileged execution or human approval is performed here."""
import copy
import json
from pathlib import Path

import pytest

from evaluation import evaluate_prepared as evaluator
from recase import prepared_data
from recase.ledger import file_digest
from scripts import verify_os_isolation
from tests.test_native_training import fixture_packet, write


def test_missing_review_and_isolation_stop_before_model_construction(tmp_path, monkeypatch):
    packet, _, _ = fixture_packet(tmp_path, monkeypatch, approve=False)
    import recase.model
    def forbidden(*a, **k):
        raise AssertionError("No model may be constructed before the gate")
    monkeypatch.setattr(recase.model, "LocalModel", forbidden)
    monkeypatch.setattr(evaluator, "model_idle", lambda: True)
    out = tmp_path / "blocked"
    assert evaluator.evaluate(packet, "nli_diagnostic", "base", tmp_path / "no-proof", out) == 2
    report = json.loads((out / "preflight.json").read_text())
    assert report["missing_review_count"] == 3 and not report["model_loaded"] and report["model_calls"] == 0
    assert list(out.iterdir()) == [out / "preflight.json"]


def test_live_os_probe_not_saved_boolean_controls_pass(tmp_path, monkeypatch):
    packet, _, _ = fixture_packet(tmp_path, monkeypatch)
    _, protocol, _, _ = prepared_data.load_packet(packet)
    proof = tmp_path / "proof.json"
    report = {"status": "PASS", "checks": {"running_service_uid_matches": True}, "service_user": "fixture_service",
              "evaluator_user": "fixture_evaluator", "answers": "UNIT_TEST_ONLY", "protected_root": "UNIT_TEST_ONLY",
              "answer_sha256": protocol["datasets"]["nli_validation"]["answers_sha256"]}
    write(proof, report)
    calls = []
    def denied(*args):
        calls.append(args)
        return {"status": "BLOCKED", "answer_sha256": report["answer_sha256"]}
    monkeypatch.setattr(verify_os_isolation, "verify", denied)
    with pytest.raises(PermissionError, match="Live"):
        prepared_data.verify_dataset_isolation(proof, packet, "nli_validation")
    assert len(calls) == 1
    report["checks"]["running_service_uid_matches"] = False
    write(proof, report)
    with pytest.raises(PermissionError, match="identity"):
        prepared_data.verify_dataset_isolation(proof, packet, "nli_validation")
    assert len(calls) == 1


def matched_runs():
    identity = {k: "UNIT_TEST_FIXTURE" for k in ("dataset", "task", "protocol_sha256", "scorer_sha256", "runner_sha256", "gate_sha256", "input_sha256", "answer_sha256", "platform")}
    identity.update(dataset="nli_validation", sample_ids=["fixture"], candidate=None, cycle_sha256=None,
                    model={k: "UNIT_TEST_FIXTURE" for k in ("model", "revision", "config_sha256", "tokenizer_sha256", "quantization", "prompt_sha256", "generation")})
    runs = []
    for variant in ("base", "existing_ft"):
        i = copy.deepcopy(identity)
        i.update(variant=variant)
        i["model"].update(adapter_loaded=variant != "base", adapter_sha256=None if variant == "base" else "TEST_ADAPTER")
        runs.append({"identity": i, "count": 1, "missing_predictions": 0, "runtime_failures": 0,
                     "integrity_errors": {"duplicate_ids": [], "unexpected_ids": []}, "macro_f1": 1.0})
    return runs


def compare_runs(tmp_path, runs):
    paths = []
    for j, run in enumerate(runs):
        path = tmp_path / f"run-{j}.json"
        path.write_text(json.dumps(run))
        paths.append(path)
    return evaluator.compare(paths)


def test_comparison_rejects_changed_runner_missing_rows_and_false_adapter(tmp_path):
    runs = matched_runs()
    assert compare_runs(tmp_path, runs)["dataset"] == "nli_validation"
    runs[1]["identity"]["runner_sha256"] = "changed"
    with pytest.raises(ValueError, match="Mismatched"):
        compare_runs(tmp_path, runs)
    runs = matched_runs()
    runs[1]["missing_predictions"] = 1
    with pytest.raises(ValueError, match="Incomplete"):
        compare_runs(tmp_path, runs)
    runs = matched_runs()
    runs[1]["identity"]["model"]["adapter_loaded"] = False
    with pytest.raises(ValueError, match="Actually loaded"):
        compare_runs(tmp_path, runs)


def test_candidate_comparison_cannot_use_diagnostic_or_reset_validation_cycle(tmp_path):
    runs = [copy.deepcopy(matched_runs()[1]) for _ in range(2)]
    for j, run in enumerate(runs):
        run["identity"].update(variant="candidate", candidate=f"fixture-{j}", cycle_sha256="same")
    assert len(compare_runs(tmp_path, runs)["runs"]) == 2
    runs[1]["identity"]["cycle_sha256"] = "different"
    with pytest.raises(ValueError, match="same frozen"):
        compare_runs(tmp_path, runs)
    for run in runs:
        run["identity"]["dataset"] = "nli_diagnostic"
    with pytest.raises(ValueError, match="nli_validation"):
        compare_runs(tmp_path, runs)


def test_inference_failures_remain_in_denominator_and_model_is_closed(tmp_path, monkeypatch):
    packet, _, _ = fixture_packet(tmp_path, monkeypatch)
    _, protocol, datasets, items = prepared_data.load_packet(packet)
    (packet / "task_metrics.py").write_text("# UNIT_TEST_FIXTURE: execution is replaced with the test scorer\n")
    protocol["generation"] = {"max_output_tokens": {"nli": 128}, "context_tokens": 4096}
    monkeypatch.setattr(evaluator, "load_packet", lambda _: (packet, protocol, datasets, items))
    answer_path = packet / "answers/nli_validation.jsonl"
    gate = {"status": "PASS", "answer_proof": {"answers": str(answer_path), "answer_sha256": file_digest(answer_path)}}
    monkeypatch.setattr(evaluator, "preflight", lambda *args: gate)
    class ModelFixture:
        def __init__(self, **kwargs):
            self.path = Path("UNIT_TEST_FIXTURE")
            self.max_tokens = 128
            self.info = {"backend": "UNIT_TEST_FIXTURE_NO_REAL_MLX"}
            self.tokenizer = self
            self.calls = 0
            self.closed = False
        def load(self):
            pass
        def close(self):
            self.closed = True
        def apply_chat_template(self, *args, **kwargs):
            return "UNIT_TEST_FIXTURE"
        def encode(self, *args):
            return [1]
        def infer(self, *args):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("UNIT_TEST_INFERENCE_FAILURE")
            return {"response": '{"label":"neutral"}', "seconds": 1., "prompt_tokens": 1, "generation_tokens": 2}
    import recase.model
    model = ModelFixture()
    monkeypatch.setattr(recase.model, "LocalModel", lambda **kwargs: model)
    def scorer(task, inputs, answers, predictions):
        assert len(inputs) == len(answers) == len(predictions) == 3
        assert sum(bool(r.get("runtime_error")) for r in predictions) == 1
        return {"runtime_failures": 1, "missing_predictions": 0, "count": 3}, predictions
    monkeypatch.setattr(evaluator, "load_scorer", lambda _: scorer)
    assert evaluator.evaluate(packet, "nli_validation", "base", "UNIT_TEST_OS_PROOF", tmp_path / "result") == 1
    metrics = json.loads((tmp_path / "result/metrics.json").read_text())
    assert model.closed and model.calls == metrics["model_calls"] == 3
    assert metrics["prompt_tokens"] == 2 and metrics["generation_tokens"] == 4
    assert metrics["p95_generation_seconds"] == 1
