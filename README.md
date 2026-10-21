# RE:CASE · 로컬 증거 검토실

저장소와 브랜치·커밋 규칙, 업로드 제외 범위는 [Git 작업 안내](docs/GIT_WORKFLOW.md)를 따릅니다. 실제 수집 원문·계정 DB·모델·평가 실행 결과는 저장소에 포함하지 않습니다.

최신 가상 사건 작성·다중 증거 검토는 [구현 범위와 사용법](docs/GENERAL_REASONING.md)을 참고하세요. 기능/원문 연결은 fixture로 검증했으며 실제 모델의 복잡한 추론 정확도와 운영 적용은 미완료입니다.

최신 계정 통합 검증은 [계정 복구·전환 안내](docs/ACCOUNT_RECOVERY.md)를 따릅니다. backend195/frontend14 테스트와 새123파일 후보의 합성 분석·계정/사건 백업/복구·현재 권한·재시작을 확인했습니다. 실제 운영 UID499 배포·모델 학습·자동 삭제는 미실행입니다. 아래 병행 작업/119파일 수치는 당시 이력입니다.

[이메일·비밀번호 로그인](docs/AUTHENTICATION.md)을 현재 소스와 [미리보기8123](http://localhost:8123/signup)에 적용했습니다. 계정별 기록 보존·사용자/운영자 역할 분리·기존 접근키 코드 정리를 완료했고 backend178/frontend14 tests와 합성 브라우저 흐름을 통과했습니다. 실제 UID499/8100은 변경하지 않았습니다. 아래119파일/174 tests는 개편 전 스냅샷이며 계정 DB를 포함한 운영 이전·백업/복구·복귀의 통합 검증은 후속 작업입니다.

[최신119파일 후보·DB 전환 검사](docs/RELEASE_TRANSITION.md)를 추가했습니다. 전체174개 백엔드 테스트와 새 합성 사본의 이전·새 기록 보존·schema2 코드 복귀를 확인했습니다. 실제 운영 UID499 적용·새 모델 학습·자동 삭제·완전 폐기는 아직 수행하지 않았습니다. 아래 기능별 수치는 해당 시점의 검증 이력입니다.

백업별 별도 키를 사용하는 [로컬 암호화 백업·사본 복구 검증](docs/ENCRYPTED_BACKUPS.md)을 추가했습니다. 전체164개 백엔드 테스트와 합성 CLI 흐름을 통과했으며 실제 UID499 서비스 적용·자동90/30일 삭제·키/백업 완전 폐기는 아직 수행하지 않았습니다.

사건 관리에 종료/재개·보존 보류/해제와 사유 입력을 연결했습니다. [화면·배포 후보 검증 결과](outputs/runs/20261020T164135+0900-lifecycle-ui-9152c8/RESULT.txt)는 새 합성 fixture/사본 범위이며 UID499 운영 적용·자동90/30일 삭제는 아직 수행하지 않았습니다. [현재 공개 NLI·관리자 실행 안내](docs/DELEGATED_NLI_REVIEW.md)도 확인하세요.

현재 checkout의 DB 형식은 **schema2**입니다. 기존 schema1 DB는 자동 변환하지 않으며, 서비스 중지 확인과 새 rollback 백업을 거치는 명시적 migration이 필요합니다. UID499 운영 복사본/DB에는 아직 적용하지 않았습니다. [최신 보존정책 구현 결과](outputs/runs/20261020T161845+0900-retention-lifecycle-10ab30/RESULT.txt)와 [운영 절차](docs/OPERATIONS.md)를 먼저 확인하세요. 기존 모델 서버가 실행 중이면 개발 서버를 추가 실행하지 않습니다.

기존 Qwen3-4B MLX 학습/평가 프로젝트를 이어서 만든 FastAPI·LangGraph·MCP·Vue3 시뮬레이터입니다. 합성 사건의 공개 증거를 분석하고 새 자료 공개 후 판단의 변화와 근거 원문을 확인합니다.

**상태: LOCAL_VALIDATED, 합성 로컬 흐름에 한정.** 실제 수사/유죄 판단이나 공개 서비스의 신뢰성을 검증한 모델이 아닙니다. 기존 데이터·어댑터·결과는 보존했고 새 학습은 하지 않았습니다.

## 폴더 구성

```text
frontend/             Vue 화면·로그인/회원가입, 브라우저 E2E
backend/
  recase/             FastAPI · MLX · MCP · 데이터/권한 로직
  scripts/            반입·검수·운영 도구
  training/           학습 실행
  evaluation/         평가·비교
  tests/              Python 테스트
  requirements*.txt   Python 의존성
  .env.example        백엔드 환경변수 예시

data/                 공용 데이터
outputs/              모델 어댑터·평가·실행 결과
runtime/              사건 DB·별도 계정 DB·삭제 이력
```

실행 명령은 프로젝트 루트를 기준으로 합니다. [백엔드 안내](backend/README.md), [프론트엔드 안내](frontend/README.md), [경로 변경 안내](docs/STRUCTURE.md)를 참고하세요.

## 바로 실행

현재 이 Mac은 UID499의 격리 서버가 [로컬 앱](http://localhost:8100)을 제공하고 있습니다. 현재 운영 DB·삭제 journal은 `/Users/Shared/RECASE-isolated-0385fc/state/`입니다. 검수와 다음 실행은 [사용자 안내](docs/NEXT_ACTIONS.md), 격리 서버 시작·중단은 [운영 문서](docs/OPERATIONS.md)를 따르세요. 기존 `make serve`는 별도의 개발 서버 명령이므로 현재 격리 서버와 함께 실행하지 않습니다.

격리 배포를 사용하지 않는 개발 환경에서 이 폴더의 기존 `.venv`와 모델 캐시/outputs/mlx_adapter를 사용하는 경우:

```bash
make serve
```

새 개발 환경에서는 `.venv/bin/python backend/scripts/operations.py init-deletions --deletions runtime/deletions.jsonl`로 새 독립 journal을 준비합니다. 계정 DB는 기동 시 생성되며 `/signup`에서 본인 계정을 만듭니다. 기존 DB/journal을 덮어쓰지 않습니다. schema1은 별도 migration이 필요합니다. 기존 접근키 환경변수와 무인증 serve-demo는 제거했습니다.

현재 새 로그인 화면은 [회원가입8123](http://localhost:8123/signup)과 [로그인8123](http://localhost:8123/login)입니다. 실제 비밀번호는 직접 입력합니다. ‘합성 사건 열기’ → 사건 선택 → 분석 → 인용 원문 → 새 증거 공개 → 재분석 → 비교로 진행합니다. ‘새 합성 사건 추가’는 같은 계정에 새 사건을 추가하고 이전 기록을 보존합니다. 8123은 합성 모의 모델이며 기존8100 운영 서비스의 인증 변경은 아닙니다.

```bash
make check       # 자동 테스트·문법 검사
make frontend    # npm ci 및 Vue production build
```

Python3.11/Apple Silicon의 새 환경은 [운영 문서](docs/OPERATIONS.md)의 exact lock 설치를 따릅니다. 모델은 이미 있는 캐시만 사용하며 자동 다운로드하지 않습니다. CUDA requirements.txt와 Mac 환경을 섞어 설치하지 않습니다.

## 실제 확인한 것

- Apple M5/16GiB에서 Base/기존 FT 동일54건 순차 평가, 실제 어댑터56개 LoRA 모듈 로드.
- 초기 새 고정 의존성 환경에서41개, 후속 clean 환경에서57개 테스트와 실제 Metal 추론, frontend npm ci/build.
- 실제 MLX 브라우저304/1265px: 판단 보류 → 본인 확인 자료 후 충돌 → 무관한 새 기록에서 판단 유지.
- 실제 stdio MCP/공개 증거·타인 사건 격리, 영속 SSE/취소/timeout/버전 변경/재시작, DB 백업·복구.
- 오류·취소·부분 완료 UI는 명시적 모의 서버에서 별도 확인하며 실제 모델 결과와 구분.

기존 학습/평가셋 사이의 정확 프롬프트/템플릿 중복이 발견됐습니다. FT의 합성 계약 성공률100%를 새로운 사건의 일반화 성능으로 해석할 수 없습니다. 실제 판결문과 독립 최종 평가는 승인·사람 검수·데이터 격리 확보 전 진행하지 않습니다.

## 문서

- [현황과 남은 작업](docs/PROJECT_STATUS.md), [인수인계와 재현/롤백](docs/HANDOFF.md)
- [기존 프로젝트 감사](docs/PROJECT_AUDIT.md), [검증 체크리스트](docs/EXECUTION_CHECKLIST.md)
- [평가 조건](docs/EVALUATION_PROTOCOL.md), [평가 결과와 한계](docs/EVALUATION_REPORT.md)
- [개선 효과](docs/IMPROVEMENT_REPORT.md), [구조](docs/ARCHITECTURE.md), [데이터 관리](docs/DATA_GOVERNANCE.md)
- [운영·장애·복구](docs/OPERATIONS.md), [미해결 문제](docs/ISSUES.md)

유료 호출·공개 배포·원문 외부 전송은 하지 않습니다. 실제 모델을 평가하거나 학습하기 전 실행 중인 서버를 중단하세요. 개선된 MLX 진입점은 프로세스 lock으로 중복 모델 로딩을 거부합니다. 기존 데이터/어댑터/결과 경로 덮어쓰기는 금지하며 고유 outputs/runs 경로를 사용합니다.

후속 데이터·인증·삭제 검증은 [후속 프로토콜](docs/NEXT_PHASE_PROTOCOL.md)을 따릅니다. 새 검수 대기12건은 사람 검수 전 사용하지 않으며, 현재 실제 정답 OS 격리는 BLOCKED입니다.


## 미제사건 검토와 직접 테스트

[해석·대응·사용 방법](docs/CASE_REVIEW_AND_TESTING.md)을 준비했습니다. 가상 사건12개·증거 기록48개·검토36단계 중3개 사건은 [계정 미리보기](http://localhost:8123/cases)의 ‘테스트 사건3개 추가’로 실행하고9개는 수동 검토용입니다. [전체 자료 ZIP](outputs/runs/20261021T090257+0900-user-test-kit-47fdda/RECASE-test-kit.zip)에는 입력·단계별 공개 자료·검수 대기 제안 참고표·빈 기록지가 있습니다.194개 백엔드/14개 프론트 테스트와 합성 브라우저를 확인했으며 실제 모델 성능·사건 해결률은 측정하지 않았습니다. 실제 UID499 서버에는 이번 기능을 배포하지 않았습니다.
