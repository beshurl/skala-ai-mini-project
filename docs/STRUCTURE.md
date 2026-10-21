# 프론트·백엔드 폴더 구분

후속 계정 개편으로 아래 과거 이동 표의 local-login.html은 더 이상 활성 파일이 아닙니다. 현재는 frontend/src/views/AuthView.vue와 backend/recase/accounts.py·auth_api.py를 사용합니다. 기존 구조 변경 이력은 보존합니다.

2026-10-20 KST. Python 소스를 backend/로 이동했고 기존 Vue 폴더는 frontend/로 유지했다.

| 이전 경로 | 현재 경로 |
|---|---|
| recase/ | backend/recase/ |
| scripts/의 Python 파일 | backend/scripts/ |
| training/, evaluation/, tests/ | backend/training/, backend/evaluation/, backend/tests/ |
| requirements*.txt, .env.example | backend/requirements*.txt, backend/.env.example |
| scripts/browser_e2e.mjs | frontend/scripts/browser_e2e.mjs |
| recase/templates/local-login.html | frontend/public/local-login.html |

공용 data/outputs/runtime/.venv, docs, Makefile은 루트에 유지한다. 기존 데이터·모델·DB·접근키·삭제 journal을 옮기거나 새로 생성하지 않았다. 과거 실행 로그/manifest에 기록된 옛 소스 경로는 당시 경로로 보존한다.

루트에서 `make serve`, `make check`, `make frontend`를 그대로 사용한다. 서버는 --app-dir backend를 사용하고 pytest.ini가 backend/tests와 Python 경로를 설정한다. backend/ 안에서 직접 실행해도 서버 기본 경로·MCP subprocess·모델 lock은 같은 공유 경로를 사용한다.

직접 실행 예시(프로젝트 루트):

```bash
.venv/bin/python backend/scripts/accounts.py --help
.venv/bin/python backend/scripts/operations.py --help
.venv/bin/python backend/evaluation/compare_af.py --help
```

새 학습 bundle의 소스 해시는 새 backend/ 경로를 기준으로 고정한다. 기존 실험 산출물이나 승인 상태를 자동 변환하지 않는다. 실험/권한/사람 검수 조건은 이전과 같다.
