"""Compare only a complete, condition-matched A..F result set; never fill missing rows."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.experiments import ARMS, compare_arms
from scripts.dataset_control import write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", required=True, help="Directory containing A.json through F.json")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    runs = {name: json.loads(path.read_text()) for name in ARMS if (path := Path(args.results) / (name + ".json")).is_file()}
    try:
        report = {"status": "PASS", "runs": compare_arms(runs)}
    except ValueError as error:
        report = {"status": "BLOCKED", "reason": str(error),
                  "arms": {name: "PRESENT_UNVERIFIED" if name in runs else "NOT_RUN" for name in ARMS}}
    write_new(args.out, report)
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
