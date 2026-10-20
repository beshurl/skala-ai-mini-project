#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ -z "${CYCLE:-}" || -z "${CANDIDATE:-}" || -z "${OUT:-}" ]]; then
  echo '검수/누수/OS 격리 검사 후 고정한 CYCLE, 선언된 CANDIDATE, 새 OUT을 지정하세요. approval.json boolean은 허용하지 않습니다.' >&2
  exit 2
fi
exec "$ROOT/.venv/bin/python" backend/training/train_local.py --cycle "$CYCLE" --candidate "$CANDIDATE" --out "$OUT"
