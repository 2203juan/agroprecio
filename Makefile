# AgroPrecio · comandos del proyecto
# Escribe `make` para ver la ayuda.

-include .env
export

API_PORT ?= 8000
WEB_PORT ?= 8080
PY := .venv/bin/python

.DEFAULT_GOAL := ayuda
.PHONY: ayuda instalar pipeline pipeline-rapido reentrenar api web test notebook \
        todo docker docker-pipeline docker-api docker-web docker-logs docker-parar limpiar

ayuda: ## Muestra esta ayuda
	@printf "Uso: make <comando>\n\n"
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[32m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Local ----------

instalar: ## Crea el entorno virtual e instala Python y Node
	@if command -v uv >/dev/null; then uv venv -p 3.12 .venv && uv pip install -p .venv -r requirements-dev.txt; \
	else python3 -m venv .venv && $(PY) -m pip install -r requirements-dev.txt; fi
	cd frontend && npm install

pipeline: ## Corre el pipeline completo (descarga lo nuevo del DANE)
	$(PY) main.py

pipeline-rapido: ## Corre el pipeline sin descargar (usa data/bronze)
	$(PY) main.py --sin-descarga

reentrenar: ## Corre el pipeline y fuerza un modelo nuevo
	$(PY) main.py --sin-descarga --reentrenar

api: ## Levanta la API (puerto API_PORT, 8000 por defecto)
	$(PY) -m uvicorn api.main:app --reload --port $(API_PORT)

web: ## Levanta el dashboard en http://localhost:5173
	cd frontend && API_URL=http://localhost:$(API_PORT) npm run dev

test: ## Corre los tests
	$(PY) -m pytest -q

notebook: ## Vuelve a ejecutar el notebook de exploración
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_exploracion.ipynb

todo: pipeline ## Local: pipeline y luego API + dashboard juntos
	$(MAKE) -j2 api web

# ---------- Docker ----------

docker: ## Docker: todo (pipeline, API y dashboard en http://localhost:8080)
	docker compose up --build

docker-pipeline: ## Docker: solo el pipeline
	docker compose run --rm --build pipeline

docker-api: ## Docker: solo la API (usa la base que ya existe)
	docker compose up --build --no-deps api

docker-web: ## Docker: API + dashboard, sin correr el pipeline
	docker compose up --build --no-deps api web

docker-logs: ## Docker: muestra los logs
	docker compose logs -f

docker-parar: ## Docker: apaga todo
	docker compose down

# ---------- Limpieza ----------

limpiar: ## Borra silver, gold, modelos y logs (bronze se conserva)
	rm -rf data/silver/*.parquet data/gold/*.parquet data/gold/*.db models/*.joblib models/registry.json logs/*.log logs/*.jsonl
