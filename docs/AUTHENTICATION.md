# 이메일·비밀번호 로그인

**2026-10-21 통합 검증 갱신:** [ACCOUNT_RECOVERY](ACCOUNT_RECOVERY.md)가 최신입니다. 계정 maintenance lock·암호화 사건/계정 pair·현재 자격정보/권한/비활성·소유권·재시작을195 backend/14 frontend·123파일 합성 후보에서 검증했습니다. 과거 계정 이미지는 자동 복원/폐기하지 않습니다. 아래 메인 DB 전용 도구 한계는 유지하며 새 pair 도구와 구분합니다. 실제 UID499 전환·기존 소유권 연결·계정 DB 소실 복구는 미완료입니다.

2026-10-20 현재 checkout과 localhost:8123 합성 미리보기에 적용했다. 실제 UID499/8100 서버는 별도 코드 사본의 기존 접근키 방식이며 이번에 변경하지 않았다. 119파일 이전 후보는 계정 방식 배포본이 아니다.

## 사용 방법

1. [회원가입](http://localhost:8123/signup)에서 이름·이메일·12~128자 비밀번호와 확인 값을 입력한다. 실제 비밀번호는 사용자가 브라우저에 직접 입력한다.
2. 가입 후 사건 기록으로 이동한다. ‘합성 사건 열기’를 누르면 해당 계정에 합성 사건2개를 만든다. ‘새 합성 사건 추가’는 같은 계정에 새 사건2개를 추가하며 이전 기록을 보존한다.
3. [로그인](http://localhost:8123/login)에서 같은 이메일·비밀번호로 접속하면 사건·증거 버전·분석 이력을 이어 본다. 로그아웃 또는 서버 재시작 후에도 계정과 사건 기록은 남는다.

미리보기에는 기본 계정/공유 비밀번호를 만들지 않았다. 8124의 자동 검증 계정은 별도 DB에만 있으며 사용자 미리보기 DB에 복사하지 않았다. 이메일은 로컬 계정 식별자다. 이메일 소유 확인·비밀번호 재설정 메일·소셜 로그인·MFA는 구현하지 않았다.

## 코드 구분

- `backend/recase/accounts.py`: 계정 저장·비밀번호 검증·로그인 시도 제한·세션·서버 역할 검사.
- `backend/recase/auth_api.py`: JSON 회원가입/로그인/현재 계정/로그아웃.
- `backend/recase/admin.py`: 같은 계정의 admin 역할로 접근하는 읽기 전용 운영 API.
- `backend/scripts/accounts.py`: 실제 로컬 터미널의 운영자 계정 생성·비밀번호 재설정.
- `frontend/src/auth.ts`: 공통 로그인 상태와 CSRF 클라이언트.
- `frontend/src/views/AuthView.vue`: 기존 디자인 토큰을 공유하는 로그인·회원가입 화면.

활성 경로에서 Basic/접근키·무인증 데모·별도 관리자 키 로그인을 제거했다. 예전 개인 인증 Python/CLI/테스트와 독립 로그인 HTML/CSS·CSS 생성기7파일을 제거하고 계정·권한 회귀 검사로 교체했다. 삭제 전 소스는 해당 run/source-before에 보존한다. 기존 운영 키·DB·모델·어댑터·평가 산출물과 과거 문서는 이력으로 보존했다. Store.new_demo는 백업/복구 합성 시험에서 실제 사용하므로 유지한다.

## 인증 경계

- 비밀번호는 고유 salt와 scrypt N=32768/r=8/p=3으로 저장한다. 평문 비밀번호를 DB·로그·환경변수에 저장하지 않는다. [OWASP 비밀번호 저장 지침](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)의 해당 scrypt 프로필을 참고했다.
- 계정 DB는 서비스 소유0600 일반 파일, 상위 경로는 다른 사용자가 쓰지 못하는 운영자 소유 경로를 요구한다. 사건 DB와 분리한다. 기본 `RECASE_ACCOUNTS_DB=runtime/recase.accounts.sqlite3`이며 사용자 지정 DB가 있으면 실제 기동 설정과 CLI의 --db를 맞춘다.
- 세션은 메모리에 토큰 해시만 보관하며1시간·계정당 최대5개다. HttpOnly/SameSiteStrict 쿠키, 쓰기 CSRF, loopback/Host/Origin 경계를 적용한다. 현재 localhost HTTP이므로 HTTPS에서만 Secure 쿠키를 설정한다. 공개/원격 배포 검증이 아니다.
- 사용자 ID로 사건 소유권을 검사하며 타인 사건 접근은404다. 일반 가입은 항상 user다. admin 역할은 서버 DB에서만 부여하고 세션 요청마다 재검사한다. 로그아웃·프로세스 재시작·비밀번호 재설정·비활성화·역할 변경으로 이전 세션을 거부한다.
- 기존 `RECASE_AUTH_FILE`/`RECASE_ADMIN_AUTH_FILE`을 새 앱에 전달하면 기동을 거부한다. 자동으로 무인증 모드로 떨어지지 않는다.

## 운영자 계정과 비밀번호 재설정

8123 미리보기의 운영자 계정은 사용자가 이 프로젝트 루트의 Mac 터미널에서 다음을 실행한다. `operator@example.com`은 사용할 이메일로 바꾼다. 일반 가입과 다른 이메일을 지정한다. 암호 입력은 터미널에서 숨겨지며 인자/환경변수/채팅에 넣지 않는다. Mac 관리자 암호를 요구하는 명령이 아니다.

```bash
.venv/bin/python backend/scripts/accounts.py create-admin --email operator@example.com --name 운영자 --db outputs/runs/20261020T175323+0900-account-login-127a6e/service-accounts.sqlite3
```

이후 동일 [로그인 화면](http://localhost:8123/login)에서 로그인하고 `/admin`을 연다. 첫 가입자를 자동 관리자로 승격하지 않는다. 기존 이메일을 덮어쓰거나 일반 계정을 몰래 승격하지 않는다. 기본 개발 DB라면 --db를 생략한다. 비밀번호를 잃은 계정은 같은 DB를 명시해 로컬 터미널에서 재설정한다.

```bash
.venv/bin/python backend/scripts/accounts.py reset-password --email account@example.com --db outputs/runs/20261020T175323+0900-account-login-127a6e/service-accounts.sqlite3
```

## 저장·복구·실제 서버 적용 범위

8123은 FixtureModel 합성 검증 서버다. 새 `service-cases.sqlite3`, 별도 `service-accounts.sqlite3`, 독립 `service-deletions.jsonl`을 run 아래에 사용한다. 예전 미리보기 DB와 실제 운영 DB의 기록을 자동 이관하지 않았다. 기존 소유자 세션을 임의의 새 계정에 연결하지 않는다. 원본은 보존했다.

현재 암호화 백업·전환 검사는 메인 사건 DB용이다. 새 계정 DB·현재 권한/credential_version 보존·계정/사건 결합 이전·암호화 백업/복구·코드 복귀의 전체 운영 검증은 남아 있다. 사건 DB를 복원할 때 현재 계정 DB/삭제 journal을 과거 버전으로 함께 롤백하면 안 된다. 프로세스 재시작으로 모든 웹 세션을 폐기한다. 계정 DB의 임의 파일 복사나 과거 자격정보 복원을 운영 절차로 사용하지 않는다.

`configure_local_isolation.py`/`finish_local_isolation.py`의 기존 봉인 계획은 접근키 시점용이다. 새 계정 배포에 그대로 재실행하지 않는다. 실제 UID499 전환은 현재 작업 진단·새 소스 후보·계정 데이터의 이전/복구 검증·schema2 migration·최신 journal·원래 model.lock·서비스 계정 권한 재검증을 포함한 별도 통합 작업이다. 실제 모델 추가 로드/학습·운영 서비스 중단0이다.

## 실제 검증

run `20261020T175323+0900-account-login-127a6e`: 백엔드178 tests, 프론트14 tests, typecheck/build/compileall/pip check/diff PASS. 브라우저에서 오류 로그인·확인 암호 불일치·가입/로그인/로그아웃·재시작 뒤 같은 계정/사건/분석3버전 보존·일반 계정 운영자 차단·보호 페이지 로그인 복귀를 확인했다. 합성 분석/인용/증거 공개/비교 E2E도 통과했다. 320/390px 폼 가로 넘침0과 데스크톱 배치를 확인했다. VoiceOver·교차 브라우저·실제 UID499·부하·운영 복구는 NOT_RUN이다. LOCAL_VALIDATED 범위만 주장한다.
