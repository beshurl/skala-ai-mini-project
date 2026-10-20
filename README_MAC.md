# RE:CASE Apple Silicon 16GB

## 0. Prerequisites
Apple Silicon Mac, recent macOS, Python 3.11 or 3.12 (arm64), free disk space 8GB+ recommended. Use native Terminal, not Rosetta.

## 1. Install
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-mac.txt
```

## 2. Synthetic data smoke test
```bash
python scripts/prepare_data.py
python scripts/to_mlx.py
```

## 3. Baseline evaluation
```bash
python evaluation/evaluate_mlx.py --out outputs/base_mlx --limit 15
```

## 4. Train QLoRA (quantized model)
```bash
bash training/train_mlx.sh
```

## 5. Fine-tuned evaluation and comparison
```bash
python evaluation/evaluate_mlx.py --adapter outputs/mlx_adapter --out outputs/tuned_mlx --limit 15
python scripts/compare.py outputs/base_mlx/metrics.json outputs/tuned_mlx/metrics.json
```
For final evaluation, rerun both with `--limit 54`. On memory errors, close apps and reduce `--max-seq-length` from 768 to 512; try 4 adapted layers. Check model availability and exact repo spelling before download; set `MODEL` and `--model` consistently.

## 6. Korean judgments (manual, rights-gated collection)
The court judgment browsing service is not a bulk dataset or public unrestricted scraping API. Acquire authorized files manually and place in `data/judgments_raw/`. Create a JSON manifest with each filename, `permission_confirmed: true`, and `rights_basis` describing permission. Then:
```bash
python scripts/ingest_judgments.py --input data/judgments_raw --manifest data/rights_manifest.json
```
Output is **quarantined** `data/judgments_cleaned.jsonl`, with `review_required: true`. Regex masking is incomplete; manually review and remove names, addresses, case numbers, rare identifying facts, and sensitive details. Do not feed this output directly to training. There is intentionally no automatic court-site scraper or unsupervised judgment-to-ground-truth conversion. Only after review, labeling, and case-level split should real documents be converted to SFT samples.

## Limitations
Synthetic 360 examples are highly templated, so train/test share structural patterns and scores do not indicate real-world performance. No Mac runtime or model download was executed in this container. `mlx_lm` versions and model repository compatibility may vary. Do not infer guilt or label real persons as suspects using these outputs.
