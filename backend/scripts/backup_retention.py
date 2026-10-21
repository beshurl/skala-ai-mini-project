"""Create backup receipts, verify restoration, or export a preview inventory. Never erase."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.backup_receipts import backup_inventory, create_backup, verify_backup
from recase.lifecycle import inventory
from recase.ledger import file_digest
from recase.operations_drill import regular_private
from scripts.dataset_control import write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("backup")
    for option in ("db", "target", "receipt"):
        create.add_argument("--" + option, required=True)
    verify = commands.add_parser("verify")
    for option in ("receipt", "deletions", "scratch", "out"):
        verify.add_argument("--" + option, required=True)
    export = commands.add_parser("inventory")
    for option in ("db", "deletions", "out"):
        export.add_argument("--" + option, required=True)
    export.add_argument("--receipt", action="append", default=[])
    export.add_argument("--verification", action="append", default=[])
    args = parser.parse_args()
    if args.action == "backup":
        report = create_backup(args.db, args.target, args.receipt)
    elif args.action == "verify":
        report = verify_backup(args.receipt, args.deletions, args.scratch, args.out)
    else:
        if Path(args.out).exists() or Path(args.out).is_symlink():
            raise FileExistsError("New inventory required")
        regular_private(Path(args.db).absolute(), os.geteuid())
        report = inventory(args.db)
        report["backups"] = backup_inventory(args.receipt, args.verification, args.deletions, report)
        report["inputs"] = {"journal_sha256": file_digest(args.deletions),
                            "backup_receipt_sha256": [file_digest(p) for p in args.receipt],
                            "verification_receipt_sha256": [file_digest(p) for p in args.verification]}
        write_new(args.out, report)
    print(json.dumps({"status": report.get("status", "PASS"), "action": args.action, "original_deletions_executed": 0,
                      "backup_or_key_erasure_executed": 0}))


if __name__ == "__main__":
    main()
