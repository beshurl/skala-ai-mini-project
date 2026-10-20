# 설치·실행·장애·복구

검증 환경: Apple M5/16GiB, macOS26.5.2 arm64, Python3.11.15, Node/npm. `requirements-lock-macos-arm64.txt`는 실제 환경 freeze이며 별도 새 venv 설치와 테스트를 실행했다. 다른 OS/Python/Intel Mac 검증은 NOT_RUN.

## 실행

프로젝트 루트에서:

```bash
python3.11 -m venv .venv-new
.venv-new/bin/python -m pip install -r requirements-lock-macos-arm64.txt
cd frontend
npm ci
npm run build
cd ..
.venv-new/bin/python -m uvicorn recase.api:app --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
```

이 프로젝트의 기존 `.venv`를 재사용할 때는 `make serve`, 확인은 `make check`. 브라우저 http://127.0.0.1:8100 에서 명시적 데모 입장. 새 합성 데모 시작은 새 세션/사건을 만들며 이전 DB 자료를 삭제하지 않는다.

모델 캐시는 `mlx-community/Qwen3-4B-4bit`의 이미 확보한 snapshot을 재사용한다. 자동 다운로드하지 않으므로 새 장비에는 해당 모델/토크나이저와 어댑터를 별도로 준비해야 한다. `RECASE_ADAPTER` 기본값은 outputs/mlx_adapter, `RECASE_DB` 기본값 runtime/recase.sqlite3, `RECASE_BACKEND` 기본값 mlx. `.env`는 자동으로 읽지 않으며 shell에서 필요한 항목만 export한다. API key는 필요 없다. 모델 로드 실패시 readiness 실패/시작 실패이며 조용한 Base/fixture 전환은 없다.

`RECASE_BACKEND=fixture`는 실제 모델 없는 통합 테스트용이며 화면/결과에 명확히 표시한다. 실제 모델 검증으로 보고하지 않는다. 다중 API worker와 동시에 학습/평가를 실행하지 않는다. 모델 lock 충돌은 MODEL_BUSY로 거부한다.

## 상태와 오류

- GET /health: 프로세스. GET /ready: 모델 로딩/어댑터 상태. 큐는8개/생성1개, 초과429.
- POST /api/cases/{case_id}/analyses: persisted job_id/202. GET /api/jobs/{id}: QUEUED/RUNNING/COMPLETED/PARTIAL/FAILED/CANCELLED/STALE.
- SSE /api/jobs/{id}/events: cookie 인증, Last-Event-ID 또는 after, ID/job ID 포함. 브라우저는3번 재접속 후 상태 새로고침을 제공한다.
- MODEL_OUTPUT_INVALID/RETRIEVAL_INSUFFICIENT: 부분 결과와 한계 확인. MCP_TOOL_FAILED: 도구 재시작/DB 경로·버전 확인. ANALYSIS_TIMEOUT:180초/token 경계 취소. SERVER_RESTARTED: 새 분석 요청.
- 모델 OOM: 서버를 정상 종료하고 다른 앱 메모리를 확인한다. 모델/캐시를 임의 삭제하지 않는다. 모델 선택/학습 설정 변경은 새 run에서만 수행한다.
- 디스크 부족: df 확인, 원본 데이터·어댑터·기존 결과를 삭제하지 않는다. 이전 산출물 보존 위치와 보존 정책을 먼저 확인한다.
- 로그는 access log를 끄고 영속 audit/events의 ID/상태를 사용한다. request ID는 응답 X-Request-ID, job ID는 작업/이벤트에 제공한다. 외부 LangSmith/OTEL tracing은 코드에서 명시적으로 비활성화한다.

## 백업/복구

실제 사용한 명령:

```bash
.venv/bin/python scripts/operations.py backup --db runtime/recase.sqlite3 --target outputs/runs/20261020-browser-e2e/service-backup.sqlite3
.venv/bin/python scripts/operations.py restore --db outputs/runs/20261020-browser-e2e/service-backup.sqlite3 --target outputs/runs/20261020-browser-e2e/service-restored.sqlite3
.venv/bin/python scripts/operations.py check --db outputs/runs/20261020-browser-e2e/service-restored.sqlite3
```

재실행시 새 목적지명을 지정한다. 이미 있는 파일은 거부한다. SQLite backup API로 WAL 상태를 포함하고 새 복구본에 integrity_check를 수행한다. 파일 mode0600. 실제 복구 테스트에서 사건 스냅샷 보존과 재시작시 진행 작업 실패 상태를 확인했다. 기존 DB를 덮어쓰지 않고 서버 종료 후 `RECASE_DB=<새 복구본>`으로 전환한다.

## 롤백

기존 어댑터·데이터·기존 평가 결과는 원본 해시 그대로이며 모델 재다운로드가 필요 없다. 개선 코드 전체를 되돌려야 하면 `35bfb54` 기준 커밋을 **별도 checkout/worktree**에서 확인하거나 original_project.tar.gz를 새 폴더에 푼다. 현재 작업 폴더에 reset --hard나 tar 덮어쓰기를 하지 않는다. runtime DB는 schema1이며 더 높은 schema 파일을 이 코드로 열지 않는다.

Base 서빙 전환은 이번 앱 검증 범위에서 실행하지 않았다. 오프라인 평가의 --adapter 생략으로 Base 검증은 가능하다. 서빙 모델/어댑터를 바꿀 때는 서버를 중단하고 새 설정을 고정한 별도 실행에서 readiness·인용·결과 계약을 다시 검증한다. 자동 fallback이나 실행 중 hot swap은 제공하지 않는다.

## 운영 한계

로컬 데모 범위 LOCAL_VALIDATED. 실제 인증/역할·다른 OS 사용자와 최종 정답의 파일권한 분리·보존/삭제 자동화·암호화 백업·실사용 부하·광범위 장애 복구·배포 환경 검증은 미완료. 공개 배포와 유료 호출은 수행하지 않았다. 현재 로컬 처리량을 공개 서비스 동시 사용자 수로 일반화하지 않는다.
