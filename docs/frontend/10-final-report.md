# RE:CASE 사용자 서비스·관리자 구현 보고

이 문서의 접근키/별도 관리자 인증은 작성 시점 이력입니다. 현재 checkout·8123은 이메일·비밀번호와 통합 서버 역할 방식입니다. 최신 계약·검증 범위는 [인증 안내](../AUTHENTICATION.md)를 따릅니다. 실제 UID499 운영 적용은 아직 수행하지 않았습니다.

2026-10-20 KST. **구현 및 fixture 통합은 LOCAL_VALIDATED. 실제 MLX 성공 응답의 신규 UI 전체 검증과 UID499 운영 반영은 미완료다. 전체 인수 완료/공개 운영 승격으로 판정하지 않는다.**

## 최종 구조와 화면

기존 Vue3/Vite → FastAPI → 기존 소유자 SQLite/Worker/LangGraph → 실제 stdio MCP/keyword 검색/기존 singleton 모델 구조를 유지했다. 학습·평가·모델/어댑터·OS 격리 정책을 변경하지 않았다. 관리자만 별도 인증 역할과 원문 없는 독립 관측 SQLite를 추가했다.

- `/`: 제공한 문 열림·탐정·사건 배경·증거 보드·스크롤·캐러셀·native dialog를 유지한 RE:CASE 랜딩. 13개 raster 인스턴스(고유12개)+inline SVG 바이트 보존. 실제 `/cases` CTA.
- `/cases`, `/cases/:id`: 실제 사건 선택·공개 증거·단일 분석 요청·SSE·실제 인용·새 증거·재분석·변경/유지 비교. 취소 요청과 종료를 구분한다. 뒤로가기/기록 선택/공통 timeout과 unmount 취소를 연결했다.
- `/history`, `/settings`: 현재 소유자 기록과 실제 실행 모델 정보. 자유 사건 입력·업로드·추가 질문은 기존 API 미지원으로 명시한다.
- `/admin`, `/admin/logs`, `/admin/requests`, `/admin/llm`, `/admin/rag`, `/admin/mcp`, `/admin/errors`, `/admin/system`: 별도 운영 레이아웃. 서버측 역할 검사, 실제 집계·추이·필터·페이지·상세·request/job 상관 ID, 선택적10초 조회. 미측정과 빈 결과를 구분한다.

## 실제 API와 변경 파일

기존 사용자 API는 `04-api-integration.md` 및 `01-analysis.md`의 전체 목록을 따른다. 사용자 endpoint/응답 계약·권한 검사는 보존했다. 새 `/api/admin/login|session|logout|summary|logs`만 추가했다. 기존 사건 DB 스키마 변경0. 상태/기록 API는 읽기 전용이며 도구 실행 기능이 없다.

주요 수정: frontend/src/App.vue, main.js, style.css, vite.config.js, package.json/package-lock.json, scripts/browser_e2e.mjs, README.md. 신규: src/views/{LandingView,CaseWorkspace,RecordsView,AdminView}.vue, src/{api.ts,types.ts,navigation.ts,admin.css}, src/landing/*, public/assets/landing/*, tests/*, tsconfig.json, DESIGN.md/화면 brief.

백엔드 수정: recase/api.py(호환 경로·본문 제한·관측 연결), worker.py(요청 상관·기존 모델 호출 계측), mcp_client.py(원문 없는 호출·검색 계측/안전 코드), .env.example. 신규: recase/admin.py, recase/observability.py, tests/test_admin.py. 이 작업 전부터 존재한 다른 미커밋 데이터/학습/격리 작업은 수정·초기화·커밋하지 않았다.

신규 의존성은 개발용 TypeScript5.9.3/vue-tsc3.3.13 두 개다. 공통 통신/신규 관리자·기록 화면 타입 검사에 사용한다. Vue/Vite를 유지하며 새 router/차트/관측 서버/클라우드 서비스 의존성은 없다. 기존 작업실 JS의 전면 TypeScript 전환은 수행하지 않았다.

## 검증과 실제 결과

근거: `outputs/runs/20261020T150415+0900-frontend-admin/`.

- 전체 backend104 PASS, compileall/pip check/기존 개발54건 비교 PASS. 마지막 계측 의미 수정 후 finish-backend-tests로 재확인. 원본 데이터/어댑터/평가14개 해시 전부 일치.
- npm run typecheck, npm test(5개), npm run build PASS. 마지막 API 세션 timeout 수정 후 release-frontend-checks에 기록.
- 실제 브라우저 desktop/390px: fixture의 실제 HTTP→SQLite→stdio MCP→LangGraph→fixture 모델→근거/비교 전체 PASS. 관리자8개 페이지, 로그인·원문 없는 기록·검색 문서 ID/점수·연결된6기록·필터/빈 결과·페이지·모바일 확인.
- 사용자 키만으로 관리자403, 관리자 미설정503, CSRF/Origin/키 회전/동일 사용자 키 재사용 거부, 로그 민감정보 제외, 모델/MCP 실패·빈 검색·취소/timeout/타인 접근 회귀 PASS.
- 실제 기존 MLX에는 합성 요청1건만 실행했다. model_started 후180초 초과 결과 미반환으로 취소를1회 요청했으며 15:28 최종 CANCELLED를 UI로 확인했다. 새 성공 응답/3버전 인수는 **INCOMPLETE**. 같은 요청 자동 반복0, 서버 재시작0. `/ready`200/ready=true·기존 UID499/PID41133 유지도 확인했다. 원인 미확인 상태에서 재추론하지 않았다.
- 현재 OS 정답 EACCES 재검사/광범위 브라우저·보조공학/공개 보안 검증은 NOT_RUN이다. 이전 한정된 OS 결과를 현재 재검사로 표시하지 않는다.

명령·시각·종료코드·원시 로그는 06-testing.md의 색인을 따른다. render QA는 landing-desktop.png, admin-desktop.png, admin-mobile.png, landing-mobile.png 등에 기록한다.

최신 최종 소스 검사는 seal-checks.json/seal-*.log: backend104/Node5/typecheck/build/compile/pip/diff 전부 exit0, 원본14개 전부 동일하다. MCP 화면은 도구별 실제 호출·성공률·평균 지연을 별도로 집계하고 미호출의 성공률을 null/데이터 없음으로 표시한다. HTTP/모델 ready와 MCP 초기화 상태는 독립적으로 표시한다. 기존 MLX 작업은 최종 CANCELLED이며 현재 서버 준비 상태도 확인했다.

## 문제·해결과 측정

SVG/base64 추출 구분, wrapper overflow로 인한 sticky 고장, 숨은 장면 탭 순서, rAF·listener 정리, 실제 취소 요청 표시, 초기 raw fetch의 무한 대기 가능성을 해결했다. 직접 원인이 미확인인 실제 MLX 완료 지연은 해결했다고 기록하지 않는다. 자세한 재현/수정은 09-troubleshooting.md.

기존과 동일 조건의 성능 baseline은 NOT_MEASURED다. 별도 fixture 서버에서 로그/요약 API 각20회 평균2.63/2.19ms, P95 2.94/2.73ms를 측정했다. 운영 용량/MLX 성능/속도 개선 주장이 아니다. LCP/CLS/INP/FPS/CPU·메모리 집계는 NOT_MEASURED이며 07-performance.md에 표본/방법을 기록했다.

## 실행·검토

현재 검증용 서버: `http://localhost:8123/`, `http://localhost:8123/admin`. **모의 모델 테스트 전용**이며 실제 API·stdio MCP 관측을 사용한다. 별도 preview-user/preview-admin 키와 합성 DB/독립 journal만 사용한다. 키 내용은 출력하지 않았고 Git에 추가하지 않았다. 기존8100 운영 사본에는 새 코드가 자동 반영되지 않는다.

프론트 개발/검사:

```sh
cd /Users/beshu/Downloads/recase_macos_16gb/frontend
npm ci
npm run typecheck
npm test
npm run build
RECASE_API_TARGET=http://127.0.0.1:8123 npm run dev
```

현재 검증 서버의 실제 명령(기존8123 프로세스를 중복 기동하지 않는다):

```sh
cd /Users/beshu/Downloads/recase_macos_16gb
RECASE_MODE=personal RECASE_BACKEND=fixture \
RECASE_DB=outputs/runs/20261020T150415+0900-frontend-admin/preview.sqlite3 \
RECASE_AUTH_FILE=outputs/runs/20261020T150415+0900-frontend-admin/preview-user/auth.json \
RECASE_ADMIN_AUTH_FILE=outputs/runs/20261020T150415+0900-frontend-admin/preview-admin/auth.json \
RECASE_DELETIONS=outputs/runs/20261020T150415+0900-frontend-admin/preview-deletions.jsonl \
.venv/bin/python -m uvicorn recase.api:app --app-dir backend --host 127.0.0.1 --port 8123 --workers 1 --no-access-log --log-level warning
```

운영자 인증 신규 설정과 UID499 소유권 조건은 05-admin-dashboard.md. 현재 운영 서버를 대신하는 새 MLX 서버를 추가 실행하지 않는다.

## 남은 인수 조건

1. 기존 실제 모델의 긴 응답 지연 원인 확인 후 성공 분석/근거/3버전 비교를 신규 화면에서 검증한다. 미확인 반복 추론으로 통과시키지 않는다.
2. 검토된 업데이트 절차로 UID499 코드 사본·새 관리자 config·개인키·운영 state·최신 journal·공유 model.lock을 보존하며 새 UI/API를 반영하고 실제 역할/관측을 재검증한다. 현재는 NOT_RUN.
3. 현재 서비스 UID/정답 경로의 OS 거부 확인은 별도 검증한다. 정답·미검수 판결문은 관리자 UI를 통해 반입/노출하지 않는다.
4. 자유 사건·질문 API, 승인된 참고 판례·벡터/Hybrid/Rerank, 모델 변경 이전 이력, CPU/메모리 수집, MCP timeout 세부 원인 분류, 실제 Core Web Vitals는 추가 범위다. 존재하는 기능으로 표시하지 않는다.

사람 라벨 검수·데이터 목적별 승인·새 학습·최종 평가/공개 배포 판정은 본 프론트 작업과 별개다. 유료 호출/공개 배포/원문 외부 전송은 수행하지 않았다.
