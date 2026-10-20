PYTHON ?= .venv/bin/python
RUN_ID ?= $(shell date +%Y%m%dT%H%M%S)-local

.PHONY: test serve frontend audit eval-base eval-ft compare data-audit check
test:
	$(PYTHON) -m pytest tests -q
check: test
	$(PYTHON) -m compileall -q recase evaluation scripts training tests
serve:
	$(PYTHON) -m uvicorn recase.api:app --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
frontend:
	cd frontend && npm ci && npm run build
audit:
	$(PYTHON) scripts/environment.py --out outputs/runs/$(RUN_ID)-environment.json
data-audit:
	$(PYTHON) scripts/data_audit.py --out outputs/runs/$(RUN_ID)-data-audit.json
eval-base:
	$(PYTHON) evaluation/evaluate_mlx.py --out outputs/runs/$(RUN_ID)-base --limit 54
eval-ft:
	$(PYTHON) evaluation/evaluate_mlx.py --adapter outputs/mlx_adapter --out outputs/runs/$(RUN_ID)-ft --limit 54
compare:
	$(PYTHON) scripts/compare.py $(BASE) $(TUNED)
