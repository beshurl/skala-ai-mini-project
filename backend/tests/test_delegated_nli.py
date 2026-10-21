"""UNIT_TEST_FIXTURE delegation only; never real user consent or data review."""
import copy
import json

import pytest

from recase import delegated_review as delegated, prepared_data
from recase.ledger import append_record, digest, file_digest
from scripts import review_prepared
from tests.test_native_training import fixture_packet, write, attestation


def delegated_fixture(tmp_path, monkeypatch):
    packet, history, items = fixture_packet(tmp_path, monkeypatch, approve=False)
    for item in items:
        inp = item["subject"]["input"]
        inp.update(source_id="klue_nli", source_ref="raw/klue_nli/klue_benchmark/klue-nli-v1.1/UNIT_TEST_FIXTURE.json")
        item["subject"]["rights_basis"] = "CC-BY-SA-4.0"
        item["subject_sha256"] = digest(item["subject"])
    protocol = json.loads((packet / "protocol.json").read_text())
    for name, spec in protocol["datasets"].items():
        group = [i for i in items if i["subject"]["input"]["dataset"] == name]
        write(packet / spec["inputs"], [i["subject"]["input"] for i in group], True)
        spec["inputs_sha256"] = file_digest(packet / spec["inputs"])
    write(packet / "reviews/items.jsonl", items, True)
    protocol["review_items_sha256"] = file_digest(packet / "reviews/items.jsonl")
    write(packet / "protocol.json", protocol)
    subjects = []
    for name, maximum in (("nli_train_candidates", 300), ("nli_validation", 150)):
        real = [i for i in items if i["subject"]["input"]["dataset"] == name]
        subjects.extend({"sample_id": i["sample_id"], "subject_sha256": i["subject_sha256"], "dataset": name} for i in real)
        subjects.extend({"sample_id": f"UNIT_TEST_UNUSED:{name}:{n}", "subject_sha256": digest([name, n]), "dataset": name}
                        for n in range(maximum - len(real)))
    grant = {"kind": "public_klue_nli_user_delegation_v1", "authorization_statement": delegated.STATEMENT,
        "authorized_by": "direct_user_message", "protocol_sha256": file_digest(packet / "protocol.json"),
        "scope": "local_public_development_nli_only", "human_reviewed": False, "blind_final_eligible": False,
        "maximum_training_attempts": 3, "subjects": subjects,
        "source_files": [{"path": str(packet / "LICENSE-FIXTURE"), "sha256": file_digest(packet / "LICENSE-FIXTURE")}],
        "fixture_only": "UNIT_TEST_FIXTURE_NOT_REAL_CONSENT"}
    write(packet / delegated.GRANT, grant)
    by_sha = {i["subject_sha256"]: i for i in items}
    for s in subjects:
        item = by_sha.get(s["subject_sha256"])
        requested = delegated.DATASETS[s["dataset"]]
        append_record(packet / delegated.REVIEWS, {"kind": "delegated_nli_review", "actor_kind": "delegated_ai_review",
            "human_reviewed": False, "human_attestation_created": False, "grant_sha256": file_digest(packet / delegated.GRANT),
            **s, "decision": "accept" if item else "quarantine", "label": item["subject"]["answer"]["target"]["label"] if item else None,
            "rationale": "UNIT_TEST_FIXTURE_NOT_ACTUAL_SEMANTIC_REVIEW", "privacy_disposition": "AI_LOCAL_PUBLIC_NLI_ONLY",
            "source_integrity": "PASS", "permissions": {"processing": True, requested: True},
            "license_hashes": prepared_data.license_hashes(item) if item else {}})
    seal(packet)
    return packet, history, items


def seal(packet):
    write(packet / "tool_manifest.json", {name: file_digest(packet / name) for name in
        ("protocol.json", "selection_policy.json", delegated.GRANT)})


def test_delegation_preserves_human_counts_and_diagnostic_gate(tmp_path, monkeypatch):
    packet, history, items = delegated_fixture(tmp_path, monkeypatch)
    policy = delegated.load_delegation(packet, items)
    assert delegated.review_kind(items[0], None, policy) == "delegated_ai_review"
    assert not prepared_data.permitted(items[0], policy["reviews"][items[0]["subject_sha256"]])
    assert prepared_data.status(packet)["datasets"]["nli_train_candidates"]["approved"] == 0
    assert prepared_data.audit_native_nli(packet, history)["status"] == "PASS"
    diagnostic = next(i for i in items if i["subject"]["input"]["dataset"] == "nli_diagnostic")
    assert not delegated.delegated_permitted(diagnostic, policy)
    human = {**attestation(items[0]), "action": "reject"}
    assert delegated.review_kind(items[0], human, policy) is None


@pytest.mark.parametrize("change", ["label", "purpose", "license", "source", "task", "quarantine", "human_flag"])
def test_out_of_scope_or_changed_review_is_refused(tmp_path, monkeypatch, change):
    packet, _, items = delegated_fixture(tmp_path, monkeypatch)
    policy = delegated.load_delegation(packet, items)
    item = copy.deepcopy(items[0])
    review = policy["reviews"][item["subject_sha256"]]
    if change == "label":
        review["label"] = "neutral" if review["label"] != "neutral" else "entailment"
    elif change == "purpose":
        item["subject"]["requested_use"] = "rag"
    elif change == "license":
        item["subject"]["rights_basis"] = "ACTUAL_JUDGMENT_NOT_APPROVED"
    elif change == "source":
        item["subject"]["input"]["source_id"] = "lbox"
    elif change == "task":
        item["subject"]["input"]["task"] = "summary"
    elif change == "quarantine":
        review["decision"] = "quarantine"
    else:
        # Persist a corrupt actor record: reader must fail rather than label it human.
        append_record(packet / delegated.REVIEWS, {**review, "human_reviewed": True})
        with pytest.raises(PermissionError, match="Invalid"):
            delegated.load_delegation(packet, items)
        return
    assert not delegated.delegated_permitted(item, policy)


def test_unsealed_grant_and_unknown_history_cannot_claim_blind_or_complete(tmp_path, monkeypatch):
    packet, _, items = delegated_fixture(tmp_path, monkeypatch)
    policy = delegated.load_delegation(packet, items)
    coverage = {"kind": "delegated_known_local_history_snapshot", "actor_kind": "delegated_ai_review",
        "exposures_sha256": digest([]), "grant_sha256": file_digest(packet / delegated.GRANT),
        "external_and_pretraining_exposure": "UNKNOWN", "blind_final_eligible": False, "human_attestation_created": False}
    write(packet / delegated.COVERAGE, coverage)
    manifest = json.loads((packet / "tool_manifest.json").read_text())
    manifest[delegated.COVERAGE] = file_digest(packet / delegated.COVERAGE)
    write(packet / "tool_manifest.json", manifest)
    assert delegated.known_history_covered(policy, [])
    assert not delegated.known_history_covered(policy, [{"new_exposure": "UNIT_TEST_FIXTURE"}])
    manifest.pop(delegated.GRANT)
    write(packet / "tool_manifest.json", manifest)
    with pytest.raises(PermissionError, match="Unsealed"):
        delegated.load_delegation(packet, items)


def test_source_provenance_change_revokes_delegation(tmp_path, monkeypatch):
    packet, _, items = delegated_fixture(tmp_path, monkeypatch)
    (packet / "LICENSE-FIXTURE").write_text("UNIT_TEST_CHANGED_LICENSE")
    with pytest.raises(PermissionError, match="provenance changed"):
        delegated.load_delegation(packet, items)


def test_frozen_cycle_binds_delegated_decisions_and_shared_budget(tmp_path, monkeypatch):
    from recase import native_training
    from recase.experiments import verify_frozen
    from tests.test_native_training import TokenizerFixture
    packet, history, items = delegated_fixture(tmp_path, monkeypatch)
    write(packet / delegated.COVERAGE, {"UNIT_TEST_FIXTURE": True})
    (packet / "reviews/human_reviews.jsonl").touch(mode=0o600)
    model = tmp_path / "UNIT_TEST_FIXTURE"
    model.mkdir()
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"):
        (model / name).write_text("UNIT_TEST_FIXTURE_NOT_REAL_MODEL")
    monkeypatch.setattr(native_training, "resolve_model", lambda: model)
    monkeypatch.setattr(native_training, "verify_native_isolation", lambda *args: [])
    import transformers
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **k: TokenizerFixture())
    config = tmp_path / "configs.json"
    write(config, [{"id": "fixture", "iters": 1, "rank": 8, "layers": 8, "sequence_length": 768, "learning_rate": 1e-4}])
    isolation = tmp_path / "isolation.json"
    write(isolation, {"UNIT_TEST_FIXTURE": True})
    cycle = native_training.freeze_native(packet, history, config, packet / "protocol.json", isolation, tmp_path / "frozen")
    assert cycle["max_attempts"] == 3
    assert all("delegation:" + name in cycle["bound_files"] for name in (delegated.GRANT, delegated.REVIEWS, delegated.COVERAGE))
    assert not (tmp_path / "runtime/training-attempts.jsonl").exists()
    append_record(packet / delegated.REVIEWS, {"UNIT_TEST_CHANGED_DECISION": True})
    with pytest.raises(PermissionError, match="invalidated"):
        verify_frozen(tmp_path / "frozen/cycle.json")


def test_native_adapter_identity_preserves_generated_metadata_and_weight_bytes(tmp_path):
    from recase.native_training import finalize_native_adapter
    cycle = {"audit_kind": "prepared_native_nli_v1", "model": "/UNIT_TEST/cache/revision", "model_id": "UNIT_TEST_MODEL",
             "revision": "UNIT_TEST_REVISION", "cycle_sha256": "UNIT_TEST_CYCLE"}
    out = tmp_path / "new-training-run"
    write(out / "adapter/adapter_config.json", {"model": cycle["model"], "lora_parameters": {"rank": 8}})
    weights = out / "adapter/adapters.safetensors"
    weights.write_bytes(b"UNIT_TEST_FIXTURE_NOT_REAL_MODEL_WEIGHTS")
    before = file_digest(weights)
    finalize_native_adapter(out, cycle)
    assert json.loads((out / "adapter_config.generated.json").read_text())["model"] == cycle["model"]
    assert json.loads((out / "adapter/adapter_config.json").read_text())["model"] == "UNIT_TEST_MODEL"
    assert file_digest(weights) == before
    with pytest.raises(FileExistsError):
        finalize_native_adapter(out, cycle)


def test_native_adapter_identity_refuses_wrong_base_before_mutation(tmp_path):
    from recase.native_training import finalize_native_adapter
    cycle = {"audit_kind": "prepared_native_nli_v1", "model": "/UNIT_TEST/right", "model_id": "UNIT_TEST_MODEL",
             "revision": "UNIT_TEST_REVISION", "cycle_sha256": "UNIT_TEST_CYCLE"}
    write(tmp_path / "adapter/adapter_config.json", {"model": "/UNIT_TEST/wrong"})
    (tmp_path / "adapter/adapters.safetensors").write_bytes(b"UNIT_TEST_NOT_WEIGHTS")
    before = file_digest(tmp_path / "adapter/adapter_config.json")
    with pytest.raises(ValueError, match="differs"):
        finalize_native_adapter(tmp_path, cycle)
    assert file_digest(tmp_path / "adapter/adapter_config.json") == before
    assert not (tmp_path / "adapter_config.generated.json").exists()
