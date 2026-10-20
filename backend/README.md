# RE:CASE 백엔드

FastAPI, MLX, LangGraph, MCP와 데이터·학습·평가 도구를 모은 폴더입니다.

- `recase/`: API, 모델, MCP, 저장소와 권한·데이터 통제
- `scripts/`: 반입·검수·운영·검증 CLI
- `training/`, `evaluation/`, `tests/`: 학습, 평가, Python 테스트
- `requirements*.txt`, `.env.example`: Python 의존성과 환경변수 예시

프로젝트 루트에서 기존 환경을 재사용합니다.

```bash
make serve
make check
.venv/bin/python backend/scripts/validate_local.py --out outputs/runs/NEW-validation
```

이 폴더 안에서는 `make -C .. serve`, `make -C .. check`를 사용할 수 있습니다. Python 직접 실행도 가능합니다.

```bash
# backend/에서 실행
RECASE_MODE=personal RECASE_AUTH_FILE=runtime/personal-auth/auth.json RECASE_DELETIONS=runtime/deletions.jsonl ../.venv/bin/python -m uvicorn recase.api:app --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
```

서비스 환경변수와 MLX 어댑터의 상대 경로는 프로젝트 루트에 고정됩니다. data/outputs/runtime/.venv는 루트에 유지하며 접근키·삭제 이력·기존 모델을 복사하거나 다시 생성하지 않습니다. CLI의 --out 등 나머지 명시적 상대 파일 인자는 실행 디렉터리를 기준으로 합니다.

새 환경의 설치 명령은 프로젝트 루트 기준입니다.

```bash
python3.11 -m venv .venv-new
.venv-new/bin/python -m pip install -r backend/requirements-lock-macos-arm64.txt
```

이 잠금 파일은 검증한 Apple Silicon 환경용입니다. CUDA용 requirements.txt와 혼합하지 않습니다. 모델 평가·학습 전에 실행 중인 모델 서버를 중단하며 검수/OS 격리/최대3개 후보 통제를 유지합니다.
