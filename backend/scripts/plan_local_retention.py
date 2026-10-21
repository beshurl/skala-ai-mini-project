"""Preview selected synthetic retention periods from explicit timestamp metadata."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import file_digest, utc_now
from recase.retention_schedule import plan_retention
from scripts.dataset_control import write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--at", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if Path(args.out).exists():
        raise FileExistsError("New preview destination required")
    for name in (args.inventory, args.policy):
        if Path(name).stat().st_size > 1024 * 1024:
            raise ValueError("Metadata-only files up to1MiB required")
    policy, inventory = (json.loads(Path(p).read_text()) for p in (args.policy, args.inventory))
    report = plan_retention(inventory, policy, args.at or utc_now())
    report["inputs"] = {"policy_sha256": file_digest(args.policy), "inventory_sha256": file_digest(args.inventory)}
    write_new(args.out, report)
    print(json.dumps({"status": report["status"], "eligible_for_review": report["eligible_for_review"], "delete_actions_executed": 0}))


if __name__ == "__main__":
    main()
