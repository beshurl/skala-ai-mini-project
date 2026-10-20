"""Provision a new protected local credential directory; never print the key."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.local_auth import provision


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", required=True)
    p.add_argument("--user", required=True)
    args = p.parse_args()
    print(json.dumps(provision(args.directory, args.user)))


if __name__ == "__main__":
    main()
