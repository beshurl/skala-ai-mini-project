#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || { echo '먼저 bash sh/setup_venv.sh를 실행하세요.'; exit 1; }
exec .venv/bin/python -m agent.launch
