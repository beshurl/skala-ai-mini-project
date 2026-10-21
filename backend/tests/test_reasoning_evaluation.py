"""Exposed synthetic practice/software guards only; no real model or gold claims."""
import copy
import fcntl
import json
import os
from pathlib import Path

import pytest

from evaluation import evaluate_reasoning as evaluator
from recase.ledger import digest


@pytest.fixture
def plan(tmp_path, monkeypatch):
    # Tiny metadata fixture. The integration run below uses FixtureModel only.
    monkeypatch.setattr(evaluator, "model_identity", lambda: ({"model": "UNIT_TEST_FIXTURE", "revision": "UNIT_TEST_FIXTURE", "cache_path": str(tmp_path), "adapter": str(tmp_path)}, []))
    lock = tmp_path / "model.lock";lock.touch()
    monkeypatch.setattr(evaluator, "LOCK", lock)
    out = tmp_path / "plan"
    value = evaluator.prepare(out)
    return value, out / "plan.json"


def test_plan_declares_full_denominator_and_ai_reference_scope(plan):
    value, path = plan
    assert len(value["sample_ids"]) == len(set(value["sample_ids"])) == 36
    assert not value["human_reviewed"] and not value["independent_final_set"]
    assert value["limits"]["automatic_retries"] == 0
    assert evaluator.checked_plan(path) == value


def test_tampered_plan_is_refused(plan):
    value, path = plan
    changed = copy.deepcopy(value);changed["limits"]["seconds_per_variant"] = 999999
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="PLAN_CHANGED"):
        evaluator.checked_plan(path)


def test_busy_real_model_stops_before_worker_or_database(plan, tmp_path, monkeypatch):
    value, path = plan
    def forbidden(*args, **kwargs):
        pytest.fail("No model or worker may start while the real model lock is busy")
    monkeypatch.setattr(evaluator.subprocess, "Popen", forbidden)
    with Path(value["shared_lock"]["path"]).open("r") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = evaluator.execute(path, "base", "mlx", tmp_path / "blocked")
    assert result["valid_stages"] == 0 and result["missing_or_duplicate_stages"] == 36
    assert result["ai_proposed_relation_agreement"] is None
    assert not (tmp_path / "blocked/cases.db").exists()


def test_missing_duplicate_and_unexpected_rows_never_leave_denominator(plan):
    value, _ = plan
    rows = [{"sample_id": "P01:v1"}, {"sample_id": "P01:v1"}, {"sample_id": "UNKNOWN"}]
    result = evaluator.score(value, rows, "fixture", "base", 3)
    assert result["denominator"] == result["missing_or_duplicate_stages"] == 36
    assert result["duplicate_ids"] == ["P01:v1"] and result["unexpected_ids"] == ["UNKNOWN"]
    assert result["ai_proposed_relation_agreement"] is None
    assert result["independent_final_accuracy"] == "NOT_MEASURED"


def test_worker_refuses_existing_state_before_model_construction(plan, tmp_path, monkeypatch):
    value, path = plan
    out = tmp_path / "existing";out.mkdir(mode=0o700)
    evaluator.write(out / "execution-marker.json", {"plan_sha256": value["plan_sha256"]})
    (out / "cases.db").write_bytes(b"PRESERVE_UNIT_TEST_FIXTURE")
    with pytest.raises(PermissionError, match="FRESH_PRIVATE_RUN"):
        evaluator.worker(path, "base", "fixture", out)
    assert (out / "cases.db").read_bytes() == b"PRESERVE_UNIT_TEST_FIXTURE"


def test_real_model_metadata_cannot_mislabel_base_as_adapter():
    value = {"model_identity": {"model": "UNIT_TEST_FIXTURE", "revision": "rev", "cache_path": "/unit-model", "adapter": "/unit-adapter"},
             "bound_files": [{"path": "/unit-model/config.json", "sha256": "config"},
                             {"path": "/unit-model/tokenizer.json", "sha256": "tokenizer"},
                             {"path": "/unit-adapter/adapters.safetensors", "sha256": "adapter"}]}
    info = {"backend": "mlx", "model": "UNIT_TEST_FIXTURE", "revision": "rev", "config_sha256": "config",
            "tokenizer_sha256": "tokenizer", "adapter_loaded": False, "adapter_sha256": None}
    assert evaluator.model_matches(info, value, "mlx", "base")
    assert not evaluator.model_matches(info, value, "mlx", "existing_ft")
    assert evaluator.model_matches({**info, "adapter_loaded": True, "adapter_sha256": "adapter"}, value, "mlx", "existing_ft")
    assert not evaluator.model_matches({**info, "revision": "other"}, value, "mlx", "base")


def test_complete_36_stage_api_mcp_fixture_and_source_tampering(plan, tmp_path):
    value, path = plan
    out = tmp_path / "run";out.mkdir(mode=0o700)
    evaluator.write(out / "execution-marker.json", {"plan_sha256": value["plan_sha256"]})
    assert evaluator.worker(path, "base", "fixture", out) == 0
    rows = [json.loads(line) for line in (out / "predictions.jsonl").read_text().splitlines()]
    result = evaluator.score(value, rows, "fixture", "base", 0)
    assert len(rows) == result["valid_stages"] == 36
    assert result["missing_or_duplicate_stages"] == 0
    assert result["model_calls_attempted_observed"] == 36
    assert result["exact_quote_checks"]["checked"] == result["exact_quote_checks"]["valid"] > 0
    assert result["ai_proposed_relation_agreement"] is None
    bad = copy.deepcopy(rows)
    bad[0]["result"]["findings"][0]["citations"][0]["quote"] = "NOT_IN_THE_ORIGINAL"
    assert evaluator.score(value, bad, "fixture", "base", 0)["valid_stages"] == 35
    late = copy.deepcopy(rows)
    late[0] = {**late[2], "sample_id": "P01:v1"}  # Later-stage evidence cannot masquerade as v1.
    assert evaluator.score(value, late, "fixture", "base", 0)["valid_stages"] == 35
    # Structural fixture runs cannot become a real-model comparison.
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    evaluator.write(a, result);evaluator.write(b, {**result, "variant": "existing_ft"})
    with pytest.raises(ValueError, match="REAL_COMPLETE_MATCHED"):
        evaluator.compare([a, b])
