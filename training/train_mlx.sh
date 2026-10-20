#!/usr/bin/env bash
set -euo pipefail
MODEL="${MODEL:-mlx-community/Qwen3-4B-4bit}"
mlx_lm.lora --model "$MODEL" --train --data data/mlx --batch-size 1 --num-layers 8 --iters "${ITERS:-120}" --learning-rate 1e-4 --max-seq-length 768 --grad-checkpoint --mask-prompt --adapter-path outputs/mlx_adapter --save-every 40
