# 아키텍처

Vue/Vite 단일 origin → FastAPI → 기존 소유자 Store/Worker/LangGraph → 실제 stdio MCP/keyword/MLX. 사용자 API 계약과 모델은 유지한다.

경로: / 랜딩(제공 HTML), /cases와 /cases/:id 작업실, /history 본인 기록, /settings 실행 정보, /admin 및 logs/requests/llm/rag/mcp/errors/system. 작은 History API 분기이며 새 라우터 의존성은 없다. 공통 API 클라이언트는 TypeScript, Vue의 기존 JS는 보존한다. TypeScript/vue-tsc는 개발 시 타입 검사용이다.

관리자: RECASE_ADMIN_AUTH_FILE의 별도0600 credential config가 있어야 활성화한다. 사용자 키와 같은 digest는 기동 거부. 관리자 로그인은 기존 개인 접근 인증을 통과한 로컬 사용자가 추가 키를 입력하는 단계이며 별도 HttpOnly strict cookie와 관리자 CSRF를 쓴다. 관리자 API는 cookie를 서버에서 매 요청 확인한다. 키는 프론트 환경변수/URL/로그에 넣지 않는다.

관측: 운영 DB 옆 별도 관측 SQLite(0600). 필드 allowlist, 원문/프롬프트/질문/query/헤더/쿠키/정답/경로/exception 문자열을 받지 않는다. HTTP request_id를 서버가 생성하고 분석 job trace_id와 연결한다. 스레드 ContextVar로 LLM과 MCP/검색 호출에 전달한다. 최대100,000개 retained 이벤트 안의 집계이며 관측 시작/최초 retained 시각·누락 수를 표시한다. 보관 삭제는 이 새 관측 기록에만 적용한다. 운영 사건 삭제·복구 정책과 무관하다.

UI 모델/키워드/도구 기록은 실패와 표본 수를 포함한다. 지연은 관측된 실제 wall time, 모델 응답의 토큰 필드가 없으면 null. 서버 정보는 현재 실행 상태와 backend만 표시한다. 미측정 CPU/메모리/모델 변경 이전 이력은 NOT_MEASURED이다.
