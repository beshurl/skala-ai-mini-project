"""Launch a hash-checked local review/evaluation packet after backend relocation."""
import argparse
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def validate_packet(value):
    packet = Path(value).resolve(strict=True)
    if not packet.is_relative_to(PROJECT / "outputs/runs") or not packet.is_dir():
        raise ValueError("A local prepared packet under this project's outputs/runs is required")
    if packet.stat().st_uid != os.geteuid() or packet.stat().st_mode & 0o022:
        raise PermissionError("Packet must belong to this operator and not be group/other writable")
    manifest = json.loads((packet / "tool_manifest.json").read_text())
    for name, expected in manifest.items():
        if Path(name).name != name or (packet / name).is_symlink():
            raise ValueError("Regular packet source basenames required")
        actual = hashlib.sha256((packet / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Prepared workflow code/protocol changed; a new reviewed version is required")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True)
    parser.add_argument("action", choices=("review", "preflight", "evaluate", "compare", "audit-context"))
    args, remaining = parser.parse_known_args()
    packet = validate_packet(args.prepared)
    name = "review_control.py" if args.action == "review" else "audit_context.py" if args.action == "audit-context" else "evaluate_prepared.py"
    if name not in json.loads((packet / "tool_manifest.json").read_text()):
        raise ValueError("Requested workflow source is not included in the tool seal")
    sys.path.insert(0, str(PROJECT / "backend"))
    sys.path.insert(0, str(packet))
    sys.argv = [str(packet / name), *([] if args.action in ("review", "audit-context") else [args.action]), *remaining]
    runpy.run_path(str(packet / name), run_name="__main__")


if __name__ == "__main__":
    main()
