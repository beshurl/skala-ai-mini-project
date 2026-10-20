# RE:CASE · 로컬 증거 검토실

기존 Qwen3-4B MLX 학습/평가 프로젝트를 이어서 만든 FastAPI·LangGraph·MCP·Vue3 시뮬레이터입니다. 합성 사건의 공개 증거를 분석하고 새 자료 공개 후 판단의 변화와 근거 원문을 확인합니다.

**상태: LOCAL_VALIDATED, 합성 로컬 흐름에 한정.** 실제 수사/유죄 판단이나 공개 서비스의 신뢰성을 검증한 모델이 아닙니다. 기존 데이터·어댑터·결과는 보존했고 새 학습은 하지 않았습니다.

## 폴더 구성

```text
frontend/             Vue 화면, 로그인 HTML/CSS, 브라우저 E2E
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
runtime/              DB·접근키·삭제 이력
```

실행 명령은 프로젝트 루트를 기준으로 합니다. [백엔드 안내](backend/README.md), [프론트엔드 안내](frontend/README.md), [경로 변경 안내](docs/STRUCTURE.md)를 참고하세요.

## 바로 실행

이 폴더의 기존 `.venv`와 모델 캐시/outputs/mlx_adapter를 사용하는 경우:

```bash
make serve
```

새 checkout에서는 먼저 `.venv/bin/python backend/scripts/local_auth.py --directory runtime/personal-auth --user LOCAL_USER`와 `.venv/bin/python backend/scripts/operations.py init-deletions --deletions runtime/deletions.jsonl`을 한 번 실행합니다. 기존 자격정보/삭제 journal은 덮어쓰지 않습니다. `make serve-demo`는 인증 없는 합성 데모를 명시적으로 실행합니다.

[로컬 앱](http://localhost:8100)에서 접근키로 로그인한 뒤 데모에 입장합니다. 현재 키는 runtime/personal-auth/key.txt에 mode0600으로 보관됩니다. 채팅/URL에 붙여 넣지 않습니다. 사건 선택 → 분석 → 인용 원문 확인 → 새 증거 공개 → 재분석 → 이전 결과와 비교합니다. `새 합성 데모 시작`은 별도 사건/세션을 만듭니다.

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
