# 설치·실행·장애·복구

검증 환경: Apple M5/16GiB, macOS26.5.2 arm64, Python3.11.15, Node/npm. `requirements-lock-macos-arm64.txt`는 실제 환경 freeze이며 별도 새 venv 설치와 테스트를 실행했다. 다른 OS/Python/Intel Mac 검증은 NOT_RUN.

현재 폴더 경로는 [STRUCTURE](STRUCTURE.md)를 따른다. 아래 과거 백업/복구 실행 기록은 당시 경로를 보존했다.

## 실행

프로젝트 루트에서:

```bash
python3.11 -m venv .venv-new
.venv-new/bin/python -m pip install -r backend/requirements-lock-macos-arm64.txt
cd frontend
npm ci
npm run build
cd ..
.venv-new/bin/python backend/scripts/local_auth.py --directory runtime/personal-auth --user LOCAL_USER
.venv-new/bin/python backend/scripts/operations.py init-deletions --deletions runtime/deletions.jsonl
make serve PYTHON=.venv-new/bin/python
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

로컬 데모 범위 LOCAL_VALIDATED. 실제 인증/역할·다른 OS 사용자와 최종 정답의 파일권한 분리·보존/삭제 자동화·암호화 백업·실사용 부하·광범위 장애 복구·배포 환경 검증은 미완료. 공개 배포와 유료 호출은 수행하지 않았다. 현재 로컬 처리량을 공개 서비스 동시 사용자 수로 일반화하지 않는다. 아래 후속 검증을 이 초기 한계 기록보다 우선한다.

## 개인 로컬 운영 후속 검증

사용자가 목표 환경을 이 Mac 로컬 전용으로 지정했다. `make serve`는 RECASE_MODE=personal/RECASE_AUTH_FILE/RECASE_DELETIONS를 설정한다. 새로운 자격정보는 새 디렉터리만 생성하며 비밀키는 출력하지 않는다. 보호 폴더0700, config/key 파일0600, 현재 UID 소유자만 허용한다.

브라우저는 localhost:8100의 로컬 폼으로 로그인한다. 접근키는 runtime/personal-auth/key.txt에서 복사한다. 키 자체를 채팅/URL/로그에 넣지 않는다. HttpOnly/SameSiteStrict 인증 쿠키는1시간, 서버 재기동 시 즉시 만료된다. 프로세스 안에는 토큰 해시만 보관하며 최대16세션이다. config 변경/제거/권한 오류도 인증을 거부한다. API 점검은 같은 키의 HTTP Basic 헤더를 사용할 수 있다. 단일 로컬 운영자 인증이며 원격/TLS/다중 사용자 신원 체계가 아니다. 합성 사건의 소유권과 CSRF는 별도로 계속 검사한다.

회전은 새 credential 디렉터리를 생성하고 이전 서버를 중단한 뒤 RECASE_AUTH_FILE을 새 config로 바꾸어 재기동한다. 접근키 상실 시 기존키를 덮어쓰지 않는다. `make serve-demo`는 무인증 합성 데모 선택이며 개인 운영 검증으로 보고하지 않는다.

현재 서버는 개인정보·판결문이 아닌 합성 사례만 다룬다. 실제 MLX 제한 부하 시험은6개 합성 세션/동시12요청/최대60초였다. 승인된9건 완료와 큐 초과3건429를 확인했다. 지속 부하·원격 처리량·실제 사건 품질을 측정한 결과는 아니다.

### 삭제와 복구

이전 절의 restore 명령은 역사적 실행 기록이다. 새 복구 명령은 반드시 최신 독립 --deletions journal을 요구하며 복구된 bearer 세션을 모두 폐기한다. 서버는 기동 시 journal의 미완료 삭제를 먼저 적용한다. 개인 모드에서 journal이 없으면 기동을 거부한다.

```bash
# 아래는 운영자가 명시적으로 삭제할 사건에만 실행한다. 먼저 서버를 중단한다.
.venv/bin/python backend/scripts/operations.py delete-case --db runtime/recase.sqlite3 --deletions runtime/deletions.jsonl --owner OWNER_ID --case-id CASE_ID
.venv/bin/python backend/scripts/operations.py restore --db BACKUP.sqlite3 --target NEW.sqlite3 --deletions runtime/deletions.jsonl
```

삭제 기록은 DB보다 먼저 fsync하므로 중간 중단 후 다음 기동/복구에서 재적용된다. 사건·근거·주장·작업·이벤트와 관련 세션을 제거한다. 원본 데이터·학습 어댑터·기존 평가 파일에는 이 삭제 명령을 적용하지 않았다. 실제 검증은 backend/scripts/verify_deletion_recovery.py가 만든 별도 합성 DB에서 수행했다. 기존 백업 바이트는 보존되며 자동 보존기간/암호화 키 폐기/APFS 스냅샷 완전 삭제는 미검증이다.

독립 검수/OS 격리와 파일럿 판정은 NEXT_PHASE_PROTOCOL.md와 NEXT_PHASE_REPORT.md를 따른다.
