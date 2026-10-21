# API 연결

이 문서의 접근키/별도 관리자 인증은 작성 시점 이력입니다. 현재 checkout·8123은 이메일·비밀번호와 통합 서버 역할 방식입니다. 최신 계약·검증 범위는 [인증 안내](../AUTHENTICATION.md)를 따릅니다. 실제 UID499 운영 적용은 아직 수행하지 않았습니다.

기존 사용자 API는 01-analysis.md의 계약 그대로다. 공통 api.ts는 same-origin, CSRF, 취소/15초 timeout, 구조화 오류·요청 ID를 제공한다. 자동 재시도는0이다. 상태 불확실 시 쓰기를 반복하기 전에 job 조회를 안내한다. CaseWorkspace의 실제 SSE 이벤트·Last-Event-ID 재접속과 최대3회 연결 실패 뒤 수동 복구는 유지한다.

추가한 API:

| 경로 | 계약 |
|---|---|
| POST /api/admin/login | 별도 access_key(max128), 추가 필드 거부 → role/user/csrf, 1시간 HttpOnly strict cookie(/api/admin). 1분5회 제한 |
| GET /api/admin/session | 서버 관리자 cookie 검증 → role/user/csrf |
| POST /api/admin/logout | 관리자 cookie+CSRF → 세션 폐기 |
| GET /api/admin/summary?seconds=3600 | 60초~7일, 관측 저장소 실제 집계·표본·현재 ready/model/queue/MCP/search 범위 |
| GET /api/admin/logs | seconds/component/level/q/request_id/trace_id/errors_only/limit1~100/offset0~100000 → items/total/limit/offset |

로그 검색은 파라미터 바인딩·문자열 wildcard escape. 미설정503 ADMIN_DISABLED, 관리자 세션 없음403 ADMIN_REQUIRED. 개인 운영 모드에서는 기존 로컬 인증이 추가로 선행한다. 사용자 쿠키/CSRF/접근키만으로 관리자 권한을 얻지 못한다. cookie/헤더/본문/query는 관측에 저장하지 않는다.

기존 DB 스키마 변경0. 별도 `<configured DB name>.observations.sqlite3`에 안전한 메타데이터를 저장한다. 기존 작업 결과를 읽어서 과거 토큰/지연을 소급 추정하지 않는다. 관리자 UI에는 기존 사건 원문/평가 정답/API 임의 실행 엔드포인트가 없다.
