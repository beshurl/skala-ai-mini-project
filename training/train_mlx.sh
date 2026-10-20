#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -z "${DATA:-}" ]]; then
  echo 'DATA를 검수·분할 검증이 완료된 새 MLX 데이터 경로로 지정하세요. 기존 데이터의 템플릿 분할은 일반화 검증에 실패했습니다.' >&2
  exit 2
fi
exec "$ROOT/.venv/bin/python" training/train_local.py --data "$DATA" --iters "${ITERS:-10}"
