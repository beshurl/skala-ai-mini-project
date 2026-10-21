#!/usr/bin/env python3
"""Normalize a public source collection in quarantine; no training/model requests."""
import argparse
import json
from pathlib import Path
from recase.case_corpus import prepare

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--collection", required=True, type=Path)
parser.add_argument("--output", type=Path, help="New derived version directory inside the collection")
args = parser.parse_args()
print(json.dumps(prepare(args.collection, args.output), ensure_ascii=False, indent=2))
