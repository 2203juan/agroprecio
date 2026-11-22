# AgroPrecio · project commands
# Run `make` to see the help.

-include .env
export

API_PORT ?= 8000
WEB_PORT ?= 8080
MLFLOW_PORT ?= 5002
PROMETHEUS_PORT ?= 9092
GRAFANA_PORT ?= 3002
AIRFLOW_PORT ?= 8082
PY := .venv/bin/python

.DEFAULT_GOAL := help
.PHONY: help install pipeline pipeline-fast retrain experiments api web test notebook \
        all docker docker-pipeline docker-retrain docker-api docker-web docker-logs docker-stop \
        monitoring airflow airflow-run status open clean

help: ## Show this help
	@printf "Usage: make <command>\n\n"
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[32m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Local ----------

install: ## Create the virtual env and install Python and Node deps
	@if command -v uv >/dev/null; then uv venv -p 3.12 --allow-existing .venv && uv pip install -p .venv -r requirements-dev.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -r requirements-dev.txt; fi
	cd frontend && npm install

pipeline: ## Run the full pipeline (downloads new DANE bulletins)
	$(PY) main.py

pipeline-fast: ## Run the pipeline without downloading (uses data/bronze)
	$(PY) main.py --sin-descarga

retrain: ## Run the pipeline and force a new model
	$(PY) main.py --sin-descarga --reentrenar

experiments: ## Compare model variants with walk-forward validation (~1 min)
	$(PY) -m src.model.experiments

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

docker-retrain: ## Docker: force a new model with the data already downloaded
	docker compose run --rm --build pipeline python main.py --sin-descarga --reentrenar

docker-api: ## Docker: API only (uses the existing database)
	docker compose up --build --no-deps api

docker-web: ## Docker: API + dashboard, without running the pipeline
	docker compose up --build --no-deps api web

docker-logs: ## Docker: follow the logs
	docker compose logs -f

docker-stop: ## Docker: stop everything (keeps MLflow, Prometheus, Grafana and Airflow data)
	docker compose --profile airflow down

# ---------- MLOps ----------

monitoring: ## Start MLflow, Prometheus and Grafana
	docker compose up -d --build mlflow prometheus grafana

airflow: ## Start Airflow (optional, one container)
	docker compose --profile airflow up -d --build mlflow airflow

airflow-run: ## Trigger the Airflow DAG and print the state of each task
	@./docker/airflow/run_dag.sh

status: ## Show which services are up
	@check() { curl -sf -o /dev/null -m 3 "$$2" && s="up  " || s="down"; printf "  %-11s %s  %s\n" "$$1" "$$s" "$$3"; }; \
	check Dashboard  http://localhost:$(WEB_PORT)                           http://localhost:$(WEB_PORT); \
	check API        http://localhost:$(API_PORT)/salud                     http://localhost:$(API_PORT)/docs; \
	check MLflow     http://localhost:$(MLFLOW_PORT)/health                 http://localhost:$(MLFLOW_PORT); \
	check Prometheus http://localhost:$(PROMETHEUS_PORT)/-/ready            http://localhost:$(PROMETHEUS_PORT)/targets; \
	check Grafana    http://localhost:$(GRAFANA_PORT)/api/health            http://localhost:$(GRAFANA_PORT)/d/agroprecio; \
	check Airflow    http://localhost:$(AIRFLOW_PORT)/api/v2/monitor/health http://localhost:$(AIRFLOW_PORT)

open: ## Open the dashboard, MLflow and Grafana
	@open http://localhost:$(WEB_PORT) http://localhost:$(MLFLOW_PORT) http://localhost:$(GRAFANA_PORT)/d/agroprecio

# ---------- Cleanup ----------

clean: ## Delete silver, gold, models and logs (keeps bronze)
	rm -rf data/silver/*.parquet data/gold/*.parquet data/gold/*.db models/*.joblib models/registry.json logs/*.log logs/*.jsonl
