"""Local administrator provisioning/password recovery. Passwords are entered privately."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recase.accounts import Accounts
from recase.paths import PROJECT_ROOT, workspace_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create-admin", "reset-password"))
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="운영자")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "runtime/recase.accounts.sqlite3"))
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("Run in your local terminal; passwords must not be piped, passed as arguments or sent in chat")
    path = workspace_path(args.db)
    if args.action == "reset-password" and not path.is_file():
        parser.error("Existing account database required")
    password = getpass.getpass("새 비밀번호 (12자 이상): ")
    confirmation = getpass.getpass("비밀번호 확인: ")
    if password != confirmation:
        parser.error("비밀번호가 서로 다릅니다")
    accounts = Accounts(path)
    try:
        if args.action == "create-admin":
            accounts.create(args.email, password, args.name, role="admin")
            print("운영자 계정을 만들었습니다. 웹 로그인 화면에서 로그인하세요.")
        else:
            accounts.reset_password(args.email, password)
            print("비밀번호를 변경했습니다. 해당 계정의 이전 세션은 다음 요청부터 거부됩니다.")
    finally:
        password = confirmation = ""
        accounts.close()


if __name__ == "__main__":
    main()
