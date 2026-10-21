# 보안 검토

이 문서의 접근키/별도 관리자 인증은 작성 시점 이력입니다. 현재 checkout·8123은 이메일·비밀번호와 통합 서버 역할 방식입니다. 최신 계약·검증 범위는 [인증 안내](../AUTHENTICATION.md)를 따릅니다. 실제 UID499 운영 적용은 아직 수행하지 않았습니다.

## 확인한 범위

- 기존 loopback·trusted Host·Origin/sec-fetch-site·소유자·공개 버전·capability·사용자 CSRF를 유지했다. 기존 case/job/evidence/SSE/비교 타인404 회귀 통과.
- 개인 인증을 통과해도 관리자 cookie 없이는403. 관리자 키 미설정503. 별도 config/동일 digest·파일 거부; 다른 username으로 같은 사용자 키를 재사용해도 추가 로그인에서 거부한다.
- 관리자 config는 LocalAuth의 현재 UID/0600/regular file/비 symlink/디스크 변경 시 fail-closed 규칙을 상속한다. 세션은 memory only,1시간, 재시작/키 회전/로그아웃 폐기. HttpOnly/SameSite strict/path=/api/admin. loopback HTTP이므로 Secure flag는 쓰지 않는다. 원격 서비스용 인증이 아니다.
- 관리자 로그아웃은 서버 관리자 CSRF 필요. 로그인은 동일 origin 검사와 분당5회 제한, 키 max128·추가필드 거부. 전체 쓰기 본문64KiB, 기존 개인 로그인2KiB/작업 큐8·사건별 활성 작업1개 유지.
- 로그는 허용 필드/고정 event·component·operation·route template·안전 코드/숫자/형식 검증된 ID만 저장한다. body/query/헤더/쿠키/프롬프트/원문/평가정답/경로/exception 문자열을 받는 필드가 없다. 별도 SQLite0600·최대100,000개 retained. 실패한 관측 쓰기는 dropped를 노출하며 분석 흐름을 바꾸지 않는다.
- 검색은 SQL parameter binding과 wildcard escape, 기간/문자열/페이지 상한. UI는 Vue 보간, 안전한 static asset·native dialog, eval/v-html/Markdown HTML 실행 없음. 자유 Markdown은 기존 API가 구조화된 평문 결과를 반환하므로 실행하지 않는다.
- 사용자/관리자 키를 localStorage/sessionStorage/VITE 변수/URL/Git에 두지 않는다. 검증에서도 키 내용은 출력하지 않았으며 실제 새 로그 응답에 두 preview 키가 없음을 검사했다.
- 관리자 화면에 임의 MCP 실행/파일 조회/평가 정답 조회/권한 변경 기능이 없다. 외부 tracing·유료호출·공개 배포·원문 외부 전송0.

## 보증하지 않는 범위

이 작업은 현재 UID499의 실제 정답 파일 EACCES 재검사를 수행하지 않았다(NOT_RUN). 이전에 검사된7+4경로의 OS 결과와 별개다. 기존 보호 볼륨/계정/권한/운영 state/journal/어댑터 변경0. 공개·다중 사용자·조직 인증·원격 TLS·전문 침투검증은 범위 밖이다.

현재 실제 MLX 실행이180초 이후에도 종료되지 않은 점은 운영 인수의 미해결 항목이다. 분석 취소 요청과 실제 종료를 구분해 표시하며 임의의 정상 상태를 만들지 않는다. 운영 서버에는 새 코드가 반영되지 않았다.
