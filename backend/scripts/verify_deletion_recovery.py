"""Real CLI/SQLite deletion-recovery drill on a newly created synthetic database."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.ledger import file_digest, utc_now
from recase.store import Store
from recase.paths import BACKEND_ROOT
from scripts.dataset_control import write_new


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    source, backup, restored, ledger = (out / name for name in ("source.db", "before-delete.db", "restored.db", "deletions.jsonl"))
    store = Store(source)
    session = store.new_demo()
    case, survivor = store.cases(session["user_id"])
    job = store.create_job(session["user_id"], case["id"], 1, {"backend": "operation_fixture_no_model"})
    checks = []
    def run(arguments, expected=0):
        command = [sys.executable, str(BACKEND_ROOT / "scripts" / "operations.py"), *arguments]
        started = utc_now()
        result = subprocess.run(command, text=True, capture_output=True)
        checks.append({"command": command, "started_at": started, "finished_at": utc_now(),
                       "exit_code": result.returncode, "expected_exit_code": expected,
                       "stdout": result.stdout, "stderr": result.stderr})
        assert result.returncode == expected
    run(["init-deletions", "--deletions", str(ledger)])
    run(["backup", "--db", str(source), "--target", str(backup)])
    old_backup_sha = file_digest(backup)
    run(["delete-case", "--db", str(source), "--deletions", str(ledger), "--owner", session["user_id"], "--case-id", case["id"]])
    run(["restore", "--db", str(backup), "--target", str(out / "refused.db")], expected=2)
    assert not (out / "refused.db").exists()
    run(["restore", "--db", str(backup), "--target", str(restored), "--deletions", str(ledger)])
    run(["check", "--db", str(restored)])
    invariants = {}
    for name, path in (("source", source), ("restored", restored)):
        with Store(path, read_only=True).db() as db:
            invariants[name] = {
                "deleted_case_absent": db.execute("SELECT count(*) FROM cases WHERE id=?", (case["id"],)).fetchone()[0] == 0,
                "deleted_evidence_absent": db.execute("SELECT count(*) FROM evidence WHERE case_id=?", (case["id"],)).fetchone()[0] == 0,
                "deleted_job_events_absent": db.execute("SELECT count(*) FROM events WHERE job_id=?", (job["id"],)).fetchone()[0] == 0,
                "other_case_preserved": db.execute("SELECT count(*) FROM cases WHERE id=?", (survivor["id"],)).fetchone()[0] == 1,
                "sessions_revoked": db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0,
                "integrity_ok": db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "file_mode_0600": path.stat().st_mode & 0o777 == 0o600}
    assert all(all(values.values()) for values in invariants.values())
    assert file_digest(backup) == old_backup_sha
    report = {"status": "PASS", "finished_at": utc_now(), "scope": "synthetic new SQLite DB; real offline CLI commands",
              "checks": checks, "invariants": invariants, "old_backup_bytes_preserved": True,
              "physical_or_cryptographic_erasure": "NOT_VERIFIED", "automatic_retention_schedule": "NOT_CONFIGURED"}
    write_new(out / "report.json", report)
    print(json.dumps({"status": "PASS", "commands": len(checks), "out": str(out / "report.json")}))


if __name__ == "__main__":
    main()
