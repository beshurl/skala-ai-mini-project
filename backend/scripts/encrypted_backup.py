"""New per-backup keys, authenticated encrypted backups and copy-only checks. No erase action."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.encrypted_backups import create_encrypted_backup, encrypted_inventory, verify_encrypted_backup
from recase.lifecycle import inventory
from scripts.dataset_control import write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("backup")
    for name in ("db", "target", "key", "receipt"):
        create.add_argument("--" + name, required=True)
    verify = commands.add_parser("verify")
    for name in ("receipt", "key", "deletions", "scratch", "out"):
        verify.add_argument("--" + name, required=True)
    export = commands.add_parser("inventory")
    for name in ("db", "deletions", "out"):
        export.add_argument("--" + name, required=True)
    for name in ("receipt", "verification", "key"):
        export.add_argument("--" + name, action="append", default=[])
    args = parser.parse_args()
    if args.action == "backup":
        result = create_encrypted_backup(args.db, args.target, args.key, args.receipt)
    elif args.action == "verify":
        result = verify_encrypted_backup(args.receipt, args.key, args.deletions, args.scratch, args.out)
    else:
        if Path(args.out).exists() or Path(args.out).is_symlink():
            raise FileExistsError("New inventory destination required")
        result = inventory(args.db)
        result["backups"] = encrypted_inventory(args.receipt, args.verification, args.key, args.deletions, result)
        result["encrypted_backup_scope"] = "Source-only preview; keys never included in output; automatic deletion disabled"
        write_new(args.out, result)
    print(json.dumps({"status": result.get("status", "PASS"), "action": args.action,
                      "live_deletions_executed": 0, "backup_or_key_erasure_executed": 0}))


if __name__ == "__main__":
    main()
