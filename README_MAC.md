# Apple Silicon 실행 안내

2026-10-20, Apple M5/16GiB·macOS26.5.2·Python3.11.15 arm64에서 검증했습니다. 기존100회 학습 어댑터를 재사용하며 학습을 반복할 필요가 없습니다.

기존 폴더에서는 `make serve` 후 [로컬 앱](http://127.0.0.1:8100)에 접속해 runtime/personal-auth/key.txt의 로컬 접근키로 로그인합니다. `make check`로 자동 검증하고 `make frontend`로 UI를 다시 빌드합니다.

새 Python 환경:

```bash
python3.11 -m venv .venv-new
.venv-new/bin/python -m pip install -r backend/requirements-lock-macos-arm64.txt
.venv-new/bin/python backend/scripts/local_auth.py --directory runtime/personal-auth --user LOCAL_USER
.venv-new/bin/python backend/scripts/operations.py init-deletions --deletions runtime/deletions.jsonl
make serve PYTHON=.venv-new/bin/python
```

프론트엔드를 빌드하지 않았다면 먼저 `make frontend`를 실행합니다. 모델 캐시는 로컬 Qwen3-4B-4bit snapshot, 어댑터는 outputs/mlx_adapter입니다. 새 장비의 모델 준비/다운로드는 별도 작업입니다. 정확한 환경/복구/설정은 [OPERATIONS](docs/OPERATIONS.md)를 따릅니다.

Base/FT 재평가는 서버 종료 후:

```bash
RECASE_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
make eval-base RUN_ID="$RECASE_RUN_ID"
make eval-ft RUN_ID="$RECASE_RUN_ID"
make compare BASE="outputs/runs/$RECASE_RUN_ID-base/metrics.json" TUNED="outputs/runs/$RECASE_RUN_ID-ft/metrics.json"
```

현재 결과는 [평가 보고서](docs/EVALUATION_REPORT.md)에 있습니다. 기존54건은 개발에 노출된 반복 템플릿 데이터이므로 독립 최종 평가로 사용하지 않습니다. 새 학습은 [후속 프로토콜](docs/NEXT_PHASE_PROTOCOL.md)의 사람 검수·계열/노출 감사·실제 OS 격리를 통과한 cycle을 고정해야 하며 기존 outputs/mlx_adapter에 덮어쓰지 않습니다.

실제 판결문 반입은 [용도별 권한 manifest 예시](data/rights_manifest.v2.example.json)를 따릅니다. processing을 포함한 모든 예시 권한은false이며 직접 확인한 근거가 있어야 합니다. TXT/HTML/PDF 반입 출력은 항상 격리하고 실제 사람 검수 전 학습/검색에 연결하지 않습니다. [DATA_GOVERNANCE](docs/DATA_GOVERNANCE.md)를 먼저 확인합니다.
