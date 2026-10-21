#!/usr/bin/env bash
# Prepare this project's virtual environment without installing globally.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null 2>&1 \
    || { echo "ERROR: python3가 설치되어 있지 않습니다."; exit 1; }

if [ ! -x ".venv/bin/python3" ]; then
    python3 -m venv .venv
fi

./.venv/bin/python3 -m pip install -r requirements.txt
./.venv/bin/python3 -c "import fastapi, uvicorn, langgraph, langsmith, fastmcp, mcp, httpx, dotenv; print('  필요 패키지 전부 import 성공')"

cat <<EOF

.venv 준비 완료

Ollama 모델 준비:
  ollama pull qwen3.5:2b
  ollama pull qwen3:8b

실행:
  bash sh/run_live.sh
  LLM_BACKEND=openai bash sh/run_live.sh  (OpenAI API 키 필요)
EOF
