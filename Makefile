PYTHON ?= .venv/bin/python
RUN_ID ?= $(shell date +%Y%m%dT%H%M%S)-local

.PHONY: test serve serve-demo frontend audit eval-base eval-ft compare data-audit check
test:
	$(PYTHON) -m pytest backend/tests -q
check: test
	$(PYTHON) -m compileall -q backend
serve:
	RECASE_MODE=personal RECASE_AUTH_FILE="$${RECASE_AUTH_FILE:-runtime/personal-auth/auth.json}" RECASE_DELETIONS="$${RECASE_DELETIONS:-runtime/deletions.jsonl}" $(PYTHON) -m uvicorn recase.api:app --app-dir backend --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
serve-demo:
	RECASE_MODE=demo $(PYTHON) -m uvicorn recase.api:app --app-dir backend --host 127.0.0.1 --port 8100 --workers 1 --no-access-log --no-server-header --log-level warning
frontend:
	cd frontend && npm ci && npm run build
audit:
	$(PYTHON) backend/scripts/environment.py --out outputs/runs/$(RUN_ID)-environment.json
data-audit:
	$(PYTHON) backend/scripts/data_audit.py --out outputs/runs/$(RUN_ID)-data-audit.json
eval-base:
	$(PYTHON) backend/evaluation/evaluate_mlx.py --out outputs/runs/$(RUN_ID)-base --limit 54
eval-ft:
	$(PYTHON) backend/evaluation/evaluate_mlx.py --adapter outputs/mlx_adapter --out outputs/runs/$(RUN_ID)-ft --limit 54
compare:
	$(PYTHON) backend/scripts/compare.py $(BASE) $(TUNED)
