"""Offline encrypted account/case pairs; no credential restore, deployment or erase."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.account_backups import create_pair, verify_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    backup = commands.add_parser("backup")
    for name in ("db", "accounts", "deletions", "directory", "key-directory"):
        backup.add_argument("--" + name, required=True)
    verify = commands.add_parser("verify")
    for name in ("manifest", "key-directory", "accounts", "deletions", "scratch", "out"):
        verify.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        if args.action == "backup":
            result = create_pair(args.db, args.accounts, args.deletions, args.directory, args.key_directory)
        else:
            result = verify_pair(args.manifest, args.key_directory, args.accounts, args.deletions, args.scratch, args.out)
    except (ValueError, RuntimeError, OSError, sqlite3.Error, InvalidTag) as error:
        print(json.dumps({"status": "BLOCKED", "reason": "AUTHENTICATION_FAILED" if isinstance(error, InvalidTag) else str(error),
                          "account_restore_or_live_deployment": False}))
        raise SystemExit(2)
    print(json.dumps({"status": result["status"], "action": args.action, "account_restore_or_live_deployment": False}))


if __name__ == "__main__":
    main()
