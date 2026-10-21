# RE:CASE 백엔드

최신 [계정 복구/전환](../docs/ACCOUNT_RECOVERY.md)은 backend195/frontend14·123파일 합성 후보 기준입니다. account_backup.py는 사건/계정 암호화 pair를 만들고 현재 계정 DB를 유지한 사건 복구만 검증합니다. 과거 계정 자동 복원/폐기는 없습니다. verify_release_database.py에 --accounts/--target-accounts가 필요하며 구 접근키 코드/계정 과거 사본 전환을 거부합니다. 실제 UID499 미적용입니다.

현재 인증은 accounts.py/auth_api.py의 이메일·비밀번호 계정이며 admin.py도 같은 서버 역할을 검사합니다. backend178 tests PASS, [계정/운영자 안내](../docs/AUTHENTICATION.md). 아래119파일/174 tests는 개편 전 스냅샷입니다. 실제 UID499/계정 DB의 운영 이전·백업/복구는 후속 통합 검증입니다.

최신 [배포 후보·DB 전환 검사](../docs/RELEASE_TRANSITION.md)는119파일·전체174 tests 기준입니다. verify_release_database.py가 현재 기록/결과·삭제 이력·schema·코드 SHA를 대조해 오래된 DB 복귀를 거부합니다. backup/migration/retention의 SQLite 연결도 반환 전에 명시적으로 닫습니다. 실제 UID499 배포/복귀는 미실행이며 아래 기능별 수치는 시점 이력입니다.

`recase/encrypted_backups.py`·`scripts/encrypted_backup.py`: 백업별 새 AES-256-GCM 키/nonce, 메모리 SQLite snapshot, 인증 후 새 사본 복구·현재 journal·보존 보류와90/30일 미리보기를 지원합니다. [사용법·한계](../docs/ENCRYPTED_BACKUPS.md). 전체164 tests PASS, UID499 미적용·자동 삭제/폐기0입니다. cryptography50은 app 요구사항에 명시했고 기존 macOS lock의50.0.2를 재사용했습니다.

사건 lifecycle GET은 현재 evidence_version도 반환합니다. UI는 이를 본문 버전과 대조하고 POST는 evidence_version/lifecycle_revision에 묶습니다. [이번 UI·후보 사본 검증](../outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt): backend153 tests, 실제 stdio MCP fixture 흐름 PASS. 별도115파일 후보는 미배포이며 실제 UID499 작업 진단/새 백업·migration·운영 재검증이 필요합니다.

현재 소스는 schema2의 생성/종료 시각·보존 보류·상태 revision을 사용합니다. schema1을 새 Store로 쓰면 MIGRATION_REQUIRED로 거부합니다. 운영 UID499 배포는 변경하지 않았으며, 기존 DB의 명시적 백업·migration 절차는 [운영 문서](../docs/OPERATIONS.md)의 최신 절을 따릅니다. 자동 삭제/백업·키 폐기는 꺼져 있습니다.

FastAPI, MLX, LangGraph, MCP와 데이터·학습·평가 도구를 모은 폴더입니다.

- `recase/`: API, 모델, MCP, 저장소와 권한·데이터 통제
- `scripts/`: 반입·검수·운영·검증 CLI
- `training/`, `evaluation/`, `tests/`: 학습, 평가, Python 테스트
- `requirements*.txt`, `.env.example`: Python 의존성과 환경변수 예시

프로젝트 루트에서 기존 환경을 재사용합니다.

현재 이 Mac의 운영 서버는 UID499의 별도 격리 배포입니다. 아래 serve 명령은 개발 환경용이며 격리 서버와 함께 실행하지 않습니다. 현재 운영·검수 절차는 [사용자 안내](../docs/NEXT_ACTIONS.md)를 따릅니다.

```bash
make serve
make check
.venv/bin/python backend/scripts/validate_local.py --out outputs/runs/NEW-validation
```

이 폴더 안에서는 `make -C .. serve`, `make -C .. check`를 사용할 수 있습니다. Python 직접 실행도 가능합니다.

```bash
# backend/에서 실행
RECASE_ACCOUNTS_DB=runtime/recase.accounts.sqlite3 RECASE_DELETIONS=runtime/deletions.jsonl ../.venv/bin/python -m uvicorn recase.api:app --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
```

서비스 환경변수와 MLX 어댑터의 상대 경로는 프로젝트 루트에 고정됩니다. data/outputs/runtime/.venv는 루트에 유지하며 기존 데이터·삭제 이력·모델을 복사하거나 다시 생성하지 않습니다. 별도 계정 DB는 기동 시 준비하고 웹에서 가입합니다. CLI의 --out 등 나머지 명시적 상대 파일 인자는 실행 디렉터리를 기준으로 합니다.

새 환경의 설치 명령은 프로젝트 루트 기준입니다.

```bash
python3.11 -m venv .venv-new
.venv-new/bin/python -m pip install -r backend/requirements-lock-macos-arm64.txt
```

이 잠금 파일은 검증한 Apple Silicon 환경용입니다. CUDA용 requirements.txt와 혼합하지 않습니다. 모델 평가·학습 전에 실행 중인 모델 서버를 중단하며 검수/OS 격리/최대3개 후보 통제를 유지합니다.
