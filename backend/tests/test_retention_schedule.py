import copy

import pytest

from recase.retention_schedule import plan_retention


POLICY = {"scope": "personal_loopback_synthetic_service_only", "automatic_case_deletion": False,
          "automatic_backup_disposal": False, "case_retention_days": 90, "backup_retention_days": 30}


def row(identity="a", **values):
    return {"identity_sha256": identity * 64, "data_class": "synthetic_fixture", **values}


def test_exact_boundary_and_timezone_offset_match_without_touching_sources():
    inventory = {"cases": [row(closed_at="2026-07-22T09:00:00+09:00")],
                 "backups": [row("b", created_at="2026-09-20T00:00:00Z", restore_verified=True)]}
    original = copy.deepcopy(inventory)
    result = plan_retention(inventory, POLICY, "2026-10-20T00:00:00Z")
    assert result["eligible_for_review"] == 2 and inventory == original
    assert result["delete_actions_executed"] == 0 and not result["physical_erasure_verified"]


def test_missing_anchor_unknown_data_holds_and_unverified_backups_are_never_expired():
    inventory = {"cases": [row(), row("b", data_class="actual_judgment", closed_at="2000-01-01T00:00:00Z"),
                            row("c", hold=True, closed_at="2000-01-01T00:00:00Z")],
                 "backups": [row("d", created_at="2000-01-01T00:00:00Z")]}
    result = plan_retention(inventory, POLICY, "2026-10-20T00:00:00Z")
    assert result["eligible_for_review"] == 0
    assert {r["reason"] for r in result["rows"]} == {"MISSING_EXPLICIT_ANCHOR", "EXCLUDED_DATA_CLASS", "RETENTION_HOLD", "BACKUP_RESTORE_NOT_VERIFIED"}


def test_future_dates_missing_timezone_duplicate_ids_and_active_policy_refused():
    result = plan_retention({"cases": [row(closed_at="2027-01-01T00:00:00Z")]}, POLICY, "2026-10-20T00:00:00Z")
    assert not result["rows"][0]["eligible"] and result["rows"][0]["reason"] == "FUTURE_ANCHOR"
    for inventory, policy in (({"cases": [row(closed_at="2026-01-01")]}, POLICY),
                              ({"cases": [row(), row()]}, POLICY),
                              ({}, {**POLICY, "automatic_case_deletion": True}),
                              ({}, {**POLICY, "backup_retention_days": 0})):
        with pytest.raises(ValueError):
            plan_retention(inventory, policy, "2026-10-20T00:00:00Z")
