import copy
import json

import pytest

from recase.experiments import (ARMS, IMPROVEMENT_CYCLE, MATCHED_FIELDS, candidate_configs,
                                compare_arms, reserve_candidate, verify_frozen)
from recase.ledger import append_record, digest, file_digest, read_ledger


def cycle():
    return {"state": "FROZEN", "improvement_cycle": IMPROVEMENT_CYCLE, "cycle_sha256": "test-only",
            "candidates": [{"id": name, "iters": 30, "learning_rate": 1e-4, "rank": 8, "layers": 8, "sequence_length": 768}
                           for name in ("one", "two", "three")]}


def test_failures_and_new_freeze_folders_do_not_reset_three_candidate_budget(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    value = cycle()
    reserve_candidate(ledger, value, "one")
    append_record(ledger, {"action": "training_finished", "status": "FAILED"})
    with pytest.raises(PermissionError, match="already attempted"):
        reserve_candidate(ledger, value, "one")
    value["cycle_sha256"] = "another-freeze-folder"
    reserve_candidate(ledger, value, "two")
    reserve_candidate(ledger, value, "three")
    value["candidates"][0]["id"] = "four"
    with pytest.raises(PermissionError, match="BUDGET_EXHAUSTED"):
        reserve_candidate(ledger, value, "four")
    assert len([r for r in read_ledger(ledger) if r["payload"]["action"] == "training_started"]) == 3
    with pytest.raises(ValueError):
        candidate_configs(value["candidates"] * 2)


def test_changed_frozen_data_invalidates_before_training(tmp_path):
    data = tmp_path / "train.jsonl"
    data.write_text("original")
    value = {"state": "FROZEN", "bound_files": {"train": {"path": str(data), "sha256": file_digest(data)}}}
    value["cycle_sha256"] = digest(value)
    path = tmp_path / "cycle.json"
    path.write_text(json.dumps(value))
    data.write_text("new data")
    with pytest.raises(PermissionError, match="invalidated"):
        verify_frozen(path)


def runs():
    return {name: {"identity": {**{field: "matched-test-only" for field in MATCHED_FIELDS}, "sample_ids": ["test-case"], "arm": config,
                                "adapter_sha256": "same-test-adapter" if config["adapter"] else None},
                   "model_calls": 4 if config["agent"] else 1, "prompt_tokens": 50, "generation_tokens": 20,
                   "mean_latency_s": 1, "macro_f1": 1, "invalid_rate": 0} for name, config in ARMS.items()}


def test_af_comparison_requires_all_arms_matched_information_and_reported_costs():
    result = runs()
    assert compare_arms(result)["F"]["model_calls"] == 4
    changed = copy.deepcopy(result)
    changed["E"]["identity"]["public_evidence_sha256"] = "additional-hidden-evidence"
    with pytest.raises(ValueError, match="unmatched"):
        compare_arms(changed)
    del result["C"]
    with pytest.raises(ValueError, match="six"):
        compare_arms(result)
    result = runs()
    del result["F"]["generation_tokens"]
    with pytest.raises(ValueError, match="cost/quality"):
        compare_arms(result)
