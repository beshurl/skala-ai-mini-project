"""Offline lifecycle migration, explicit transitions and metadata-only inventory."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.lifecycle import inventory, migrate_v1, private_file
from recase.retention import stopped_database
from recase.store import Store
from scripts.dataset_control import write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("migrate", "inventory", "close", "reopen", "hold", "release_hold"))
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rollback-backup")
    parser.add_argument("--owner")
    parser.add_argument("--case-id")
    parser.add_argument("--evidence-version", type=int)
    parser.add_argument("--lifecycle-revision", type=int)
    parser.add_argument("--reason")
    args = parser.parse_args()
    if Path(args.out).exists() or Path(args.out).is_symlink():
        raise FileExistsError("New report required")
    private_file(Path(args.db).absolute(), os.geteuid())
    if args.action == "migrate":
        if not args.rollback_backup:
            parser.error("--rollback-backup new destination required")
        report = migrate_v1(args.db, args.rollback_backup)
    elif args.action == "inventory":
        report = inventory(args.db)
    else:
        if not all((args.owner, args.case_id, args.evidence_version, args.lifecycle_revision, args.reason)):
            parser.error("Explicit case owner, ID, observed versions and reason required")
        with stopped_database(args.db):
            report = Store(args.db).transition_case(args.owner, args.case_id, args.evidence_version,
                args.lifecycle_revision, args.action, args.reason)
    write_new(args.out, report)
    print(json.dumps({"status": report.get("status", "PASS"), "action": args.action,
                      "deletions_executed": 0, "report": args.out}))


if __name__ == "__main__":
    main()
