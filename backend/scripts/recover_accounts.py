"""Stage disabled identities from encrypted backups; review and seal locally."""
import argparse
import getpass
import json
import sqlite3
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.account_state import account_snapshot
from recase.identity_recovery import QUARANTINE_VERSION, activate_user, load_recovery, seal_recovery, stage_identities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    stage = commands.add_parser("stage")
    for name in ("manifest", "key-directory", "db", "proof"):
        stage.add_argument("--" + name, required=True)
    activate = commands.add_parser("activate-user")
    for name in ("db", "proof", "email"):
        activate.add_argument("--" + name, required=True)
    activate.add_argument("--user-id", help="Optional known identity; the exact ID must still be typed at the local prompt")
    seal = commands.add_parser("seal")
    for name in ("db", "proof", "out"):
        seal.add_argument("--" + name, required=True)
    args = parser.parse_args()
    # Refuse noninteractive input BEFORE touching recovery DB/proof/credentials.
    if args.action != "stage" and not sys.stdin.isatty():
        parser.error("Identity checks, new passwords and sealing require your local terminal; no piped approval or password")
    password = confirmation = ""
    try:
        if args.action == "stage":
            result = stage_identities(args.manifest, args.key_directory, args.db, args.proof)
        else:
            load_recovery(args.proof, args.db)
            _, rows, _ = account_snapshot(args.db, (QUARANTINE_VERSION,))
            if args.action == "activate-user":
                row = next((r for r in rows if r["email"] == args.email and (not args.user_id or r["id"] == args.user_id)), None)
                if not row or row["enabled"]:
                    raise ValueError("EXACT_DISABLED_RECOVERY_IDENTITY_REQUIRED")
                print("계정:", row["email"], row["id"], "— 운영자 권한은 부여하지 않습니다.")
                if input("소유권을 직접 확인했으면 위 계정 ID를 입력하세요: ").strip() != row["id"]:
                    raise ValueError("LOCAL_IDENTITY_CONFIRMATION_REQUIRED")
                reason = input("확인 근거 요약 (원문·비밀번호 제외): ").strip()
                password = getpass.getpass("새 비밀번호 (12자 이상): ")
                confirmation = getpass.getpass("비밀번호 확인: ")
                if password != confirmation:
                    raise ValueError("PASSWORD_CONFIRMATION_MISMATCH")
                result = activate_user(args.db, args.proof, args.email, row["id"], password, reason)
            else:
                held = {r["id"] for r in rows if not r["enabled"]}
                print("활성 일반 계정:", len(rows)-len(held), "보류:", len(held), "운영자: 0")
                expected = "보류 " + str(len(held)) + "개 유지"
                if input("미확인 계정은 비활성으로 남깁니다. '" + expected + "' 입력: ").strip() != expected:
                    raise ValueError("EXPLICIT_HELD_IDENTITIES_ACKNOWLEDGEMENT_REQUIRED")
                result = seal_recovery(args.db, args.proof, args.out, held)
    except (ValueError, RuntimeError, OSError, sqlite3.Error, InvalidTag, HTTPException) as error:
        reason = "AUTHENTICATION_FAILED" if isinstance(error, InvalidTag) else error.detail if isinstance(error, HTTPException) else str(error)
        print(json.dumps({"status": "BLOCKED", "reason": reason, "deployment_executed": False}))
        return 2
    finally:
        password = confirmation = ""
    print(json.dumps({"status": result["status"], "action": args.action, "deployment_executed": False,
                      "historical_credentials_restored": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
