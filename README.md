# RE:CASE — local fine-tuning starter

This is a **synthetic-data smoke-test baseline**, NOT a validated criminal investigation model. The included dataset is deliberately template-based and is unsuitable as evidence of real-world reasoning capability. Never infer guilt from this model.

## 1. Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_data.py
```

## 2A. NVIDIA GPU (CUDA)

Use Linux or WSL2 with an NVIDIA GPU and compatible CUDA PyTorch installation. Install CUDA-compatible PyTorch per pytorch.org, then `pip install bitsandbytes`. Check `python -c "import torch;print(torch.cuda.is_available())"`.

```bash
python training/train_cuda.py --model Qwen/Qwen3-0.6B --epochs 1
python evaluation/evaluate.py --model Qwen/Qwen3-0.6B --out outputs/base
python evaluation/evaluate.py --model Qwen/Qwen3-0.6B --adapter outputs/adapter --out outputs/tuned
```

## 2B. Apple Silicon Mac

The CUDA script does **not** work on Mac. Use Apple's MLX-LM:

```bash
pip install mlx-lm
python -m mlx_lm.lora --help
```

Consult the installed CLI help for your mlx-lm version; its flags and data schema can change. Convert `train.jsonl` and `val.jsonl` into the chat/message or text format required by your installed version before training. Intel Macs without Apple Silicon cannot use MLX. Mac MLX adapters are not interchangeable with PEFT adapters.

## 3. Real Korean court data

Before importing real documents: verify licensing/permissions; document provenance; de-identify names, addresses, unique identifiers and indirect identifiers; manually inspect a sample; split by **case** not by sentence; keep test cases isolated. The supplied generator intentionally does not scrape or reproduce real judgments. Never put `ground_truth` in the prompts or RAG index.

## 4. Honest evaluation

`evaluation/evaluate.py` measures label accuracy and macro F1, invalid output rate, and latency. Synthetic template scores do **not** demonstrate forensic reliability. Add expert-reviewed cases, evidence-ID citation verification, abstention tests, counterfactual tests and leakage checks before claiming improvements. Base and tuned runs should use identical decoding and held-out cases.

## 5. Integration

Only after validating the classifier: expose case lookup through an MCP tool and use LangGraph for statement, timeline, evidence and skeptical-review agents. Keep evidence provenance and human approval for any consequential output.
