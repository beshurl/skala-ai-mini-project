"""Rights-gated local TXT/HTML/PDF import. All outputs remain quarantined."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ingestion import ingest, clean


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output", default="outputs/runs/" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "-ingest")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    try:
        result = ingest(a.input, a.manifest, a.output, a.limit, a.dry_run, a.resume)
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        p.exit(2, type(error).__name__ + ": input/manifest/output validation failed\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["denied"] or result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
