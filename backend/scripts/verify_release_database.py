"""Check an offline release/database switch without deploying or changing DB content."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.release_validation import check_transition


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-db", "target-db", "deletions", "release-manifest", "release-root", "out"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--accounts")
    p.add_argument("--target-accounts")
    args = p.parse_args()
    try:
        result = check_transition(args.source_db, args.target_db, args.deletions,
                                  args.release_manifest, args.release_root, args.out, args.accounts, args.target_accounts)
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error), "database_mutations": 0}))
        raise SystemExit(2)
    print(json.dumps({"status": result["status"], "source_schema": result["source_schema"],
                      "target_schema": result["target_schema"], "database_mutations": 0}))


if __name__ == "__main__":
    main()
