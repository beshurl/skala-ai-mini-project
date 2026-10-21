# RE:CASE 프론트·관리자 분석

이 문서의 접근키/별도 관리자 인증은 작성 시점 이력입니다. 현재 checkout·8123은 이메일·비밀번호와 통합 서버 역할 방식입니다. 최신 계약·검증 범위는 [인증 안내](../AUTHENTICATION.md)를 따릅니다. 실제 UID499 운영 적용은 아직 수행하지 않았습니다.

2026-10-20 KST. 코드 변경 전 조사. 대상은 이 Mac 로컬 전용 개발 checkout이다. 현재 UID499/8100 격리 배포는 별도 코드 사본이며 자동 교체하지 않는다.

## 확인한 구조

- frontend: Vue 3.5.44 / Vite 8.3.4, 단일 App.vue와 CSS. 실제 사건 선택·SSE·인용·비교 구현. 라우터/공통 API 타입/관리자 화면 없음.
- backend: FastAPI create_app → SQLite Store → 단일 Worker → bounded LangGraph(scope/retrieve/analyze/verify/finalize). MLX Qwen3-4B 4-bit/기존56 LoRA/프로세스 잠금, 생성 동시성1. 모델/학습/평가 계약 변경 불필요.
- 검색: 공개된 현재 사건의 keyword-bigram-v1. vector DB, hybrid, rerank 없음. 참고 판례 검색은 BLOCKED. MCP stdio의 get_public_case/read_evidence/search_case_evidence/search_reference_judgments만 허용.
- 인증: 개인 접근키(LocalAuth) + 1시간 HttpOnly/SameSite strict 세션, 합성 데모 소유자 세션/CSRF, loopback/Host/Origin 검사. 별도 관리자 역할 없음.
- 로그: jobs/events/audit 영속 저장. 요청 지연/실패한 모델 호출/MCP 지연에 대한 안전한 관리자 조회 API 없음. 외부 tracing 비활성. 신규 독립 로컬 SQLite 관측 저장소로 최소 계측을 추가한다. 기존 DB 스키마/평가·모델·삭제 journal은 수정하지 않는다.
- 검증: pytest backend/tests, make check, npm run build, CUA용 browser_e2e.mjs. 기존 원본 산출물은 audit manifest로 보존. Docker/외부 배포를 추가할 필요 없음.

## 현재 API 계약

| 경로 | 입력 → 출력 |
|---|---|
| GET /health, /ready | 상태 / ready와 실제 model.info |
| GET /login, POST /api/local-login | form access_key → 로컬 인증 쿠키/303 |
| POST /api/demo | 명시적 합성 입장 → user_id, csrf, 세션 쿠키 |
| GET /api/session | 소유자·csrf·model |
| POST /api/demo/new | CSRF → 새 합성 소유자·사건 |
| GET /api/cases | 현재 소유자의 id/title/summary/version 배열 |
| GET /api/cases/{id} | 현재 공개 증거/주장/버전/pending_count |
| GET /api/cases/{id}/evidence/{eid} | 권한 있는 공개 원문·구간 |
| POST /api/cases/{id}/release | evidence_version → 갱신된 공개 snapshot |
| POST /api/cases/{id}/analyses | evidence_version → 202 job; 서버 중복·큐 제한 |
| GET /api/cases/{id}/analyses | 이 사건의 최신100개 job |
| GET /api/jobs/{id} | 상태/result/error/model/version |
| POST /api/jobs/{id}/cancel | CSRF → 작업 취소 요청 |
| GET /api/jobs/{id}/events | SSE 영속 이벤트; Last-Event-ID/after 재접속 |
| GET /api/cases/{id}/compare?before=&after= | 시간 순서/소유자 검사 → 양쪽 근거와 변경 여부 |

쓰기 CSRF, owner/capability 검사는 유지한다. 자유 사건 업로드·질문/대화 API는 없다. 사건 선택과 새 증거 공개/재분석을 제공하고 자유 입력/추가 질문은 미지원으로 명시한다.

## 제공 HTML

원본 BLACKWOOD_CASE_Interactive_Hero.html과 앞선 문구 개편 RECASE_Interactive_Hero.html을 조사했다. 문 두 장/배경/안개/탐정/소품/증거보드/카드의14개 embedded image, sticky 4000px scene, 스크롤 단계, 포인터 parallax, 무한 카드 캐러셀, native dialog가 핵심이다. 외부 이미지/폰트 요청 없음. 이미지 바이트와 애니메이션 수식은 재사용한다. Vue 수명 주기에 맞게 정적 템플릿/CSS/연출 모듈을 분리하고 정리 함수를 둔다. 숨은 장면/카드는 inert/탭 순서 제어, reduced-motion은 이동 효과를 줄이며 콘텐츠·CTA 유지한다. 이미지는 별도 로컬 파일로 추출해 HTML base64 중복을 제거한다.

## 구현 결정과 순서

1. 분석/계획/진행 문서(현재 단계).
2. 기존 Vue 유지, 최소 경로 분기와 공통 타입/API 클라이언트/상태/레이아웃. 정적 검사·빌드.
3. 제공 HTML 랜딩을 /에 통합. /cases CTA, 기존 작업 화면을 /cases와 /cases/:id에 연결. 브라우저 desktop/mobile 검증.
4. 별도 관리자 키 설정·세션/CSRF·서버 role gate. 미설정 시 실패 폐쇄. 안전한 HTTP/LLM/검색/MCP 계측과 읽기 전용 관리자 API, 테스트.
5. /admin 하위8페이지: 실제 집계/기록/필터/상관 ID/페이지/새로고침/빈값. 실제 데이터 계약 연결.
6. 전체 회귀·브라우저·보안·측정·최종 문서. live 모델을 중복 로드하지 않으며 실제 MLX 브라우저 전체 검증이 운영 교체를 요구하면 NOT_RUN으로 구분한다.

## 충돌·제약

기존 미커밋 작업·데이터·어댑터·평가·보호 볼륨·운영 state/credentials/launchd는 보존한다. 코드/모델/데이터 사본을 외부에 보내지 않는다. 실제 UID499 검증과 개발 UID501의 fixture 검증을 혼동하지 않는다. 신규 관리자 관측은 새 기록 이후만 집계하며 이전 데이터에 소급 측정값을 만들지 않는다. HTTP 지연은 응답 헤더까지(특히 SSE 전체 수명 아님)라고 표시한다. 실제 서비스 교체·관리자 비밀키 provisioning은 사용자가 검토할 수 있게 별도 절차로 문서화한다.
