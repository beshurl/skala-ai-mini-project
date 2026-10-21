"""Metadata-only retention preview. No deletion, filesystem access or scheduler."""
from datetime import datetime, timedelta, timezone


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Explicit timezone required")
    return parsed.astimezone(timezone.utc)


def plan_retention(inventory, policy, at):
    clock = instant(at)
    if (policy.get("scope") != "personal_loopback_synthetic_service_only"
            or policy.get("automatic_case_deletion") is not False or policy.get("automatic_backup_disposal") is not False):
        raise ValueError("Only a non-active synthetic-local preview policy is supported")
    rows = []
    for kind, collection, days_field, anchor in (("case", "cases", "case_retention_days", "closed_at"),
                                                ("backup", "backups", "backup_retention_days", "created_at")):
        days = policy.get(days_field)
        if type(days) is not int or not 1 <= days <= 3650:
            raise ValueError("Selected retention days1..3650 required")
        values = inventory.get(collection, [])
        if not isinstance(values, list) or len(values) > 1000:
            raise ValueError("Bounded metadata inventory required")
        seen = set()
        for item in values:
            identity = item.get("identity_sha256")
            if (not isinstance(identity, str) or len(identity) != 64
                    or any(c not in "0123456789abcdef" for c in identity) or identity in seen):
                raise ValueError("Unique SHA256 identities required; paths are not accepted")
            seen.add(identity)
            row = {"kind": kind, "identity_sha256": identity, "eligible": False, "anchor": anchor,
                   "retention_days": days, "expires_at": None}
            if item.get("hold") is True:
                row["reason"] = "RETENTION_HOLD"
            elif item.get("data_class") != "synthetic_fixture":
                row["reason"] = "EXCLUDED_DATA_CLASS"
            elif kind == "backup" and item.get("restore_verified") is not True:
                row["reason"] = "BACKUP_RESTORE_NOT_VERIFIED"
            elif not item.get(anchor):
                row["reason"] = "MISSING_EXPLICIT_ANCHOR"
            else:
                start = instant(item[anchor])
                row["expires_at"] = (start + timedelta(days=days)).isoformat()
                if start > clock:
                    row["reason"] = "FUTURE_ANCHOR"
                else:
                    row["eligible"] = clock >= start + timedelta(days=days)
                    row["reason"] = "ELIGIBLE_FOR_OPERATOR_REVIEW" if row["eligible"] else "WITHIN_RETENTION"
            rows.append(row)
    return {"status": "PREVIEW_ONLY", "at": clock.isoformat(), "rows": rows,
            "eligible_for_review": sum(r["eligible"] for r in rows), "delete_actions_executed": 0,
            "automatic_deletion_enabled": False, "physical_erasure_verified": False,
            "excluded_assets": ["original datasets/adapters/evaluations", "protected answers/keys", "credentials", "latest independent deletion journal"]}
