# AgroPrecio · project commands
# Run `make` to see the help.

-include .env
export

API_PORT ?= 8000
WEB_PORT ?= 8080
PY := .venv/bin/python

.DEFAULT_GOAL := help
.PHONY: help install pipeline pipeline-fast retrain api web test notebook \
        all docker docker-pipeline docker-api docker-web docker-logs docker-stop clean

help: ## Show this help
	@printf "Usage: make <command>\n\n"
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[32m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Local ----------

install: ## Create the virtual env and install Python and Node deps
	@if command -v uv >/dev/null; then uv venv -p 3.12 .venv && uv pip install -p .venv -r requirements-dev.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -r requirements-dev.txt; fi
	cd frontend && npm install

pipeline: ## Run the full pipeline (downloads new DANE bulletins)
	$(PY) main.py

pipeline-fast: ## Run the pipeline without downloading (uses data/bronze)
	$(PY) main.py --sin-descarga

retrain: ## Run the pipeline and force a new model
	$(PY) main.py --sin-descarga --reentrenar

api: ## Start the API (port API_PORT, 8000 by default)
	$(PY) -m uvicorn api.main:app --reload --port $(API_PORT)

web: ## Start the dashboard at http://localhost:5173
	cd frontend && API_URL=http://localhost:$(API_PORT) npm run dev

test: ## Run the tests
	$(PY) -m pytest -q

notebook: ## Re-run the exploration notebook
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_exploracion.ipynb

all: pipeline ## Local: pipeline, then API + dashboard together
	$(MAKE) -j2 api web

# ---------- Docker ----------

docker: ## Docker: everything (pipeline, API and dashboard at http://localhost:8080)
	docker compose up --build

docker-pipeline: ## Docker: pipeline only
	docker compose run --rm --build pipeline

docker-api: ## Docker: API only (uses the existing database)
	docker compose up --build --no-deps api

docker-web: ## Docker: API + dashboard, without running the pipeline
	docker compose up --build --no-deps api web

docker-logs: ## Docker: follow the logs
	docker compose logs -f

docker-stop: ## Docker: stop everything
	docker compose down

# ---------- Cleanup ----------

clean: ## Delete silver, gold, models and logs (keeps bronze)
	rm -rf data/silver/*.parquet data/gold/*.parquet data/gold/*.db models/*.joblib models/registry.json logs/*.log logs/*.jsonl
