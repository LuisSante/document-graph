CONDA_ENV_PATH = $(shell conda info --base)/envs/docgraph
PYTHON = $(CONDA_ENV_PATH)/bin/python
PIP = $(CONDA_ENV_PATH)/bin/pip
UVICORN = $(CONDA_ENV_PATH)/bin/uvicorn
NPM = npm --prefix client

.PHONY: setup-backend setup-frontend setup dev help

help:
	@echo "Comandos disponibles:"
	@echo "  make setup          - Instala dependencias de backend y frontend"
	@echo "  make dev            - Arranca ambos servidores (paralelo)"

setup: setup-backend setup-frontend

setup-backend:
	@echo "Instalando dependencias de Python en entorno Conda..."
	$(PIP) install fastapi uvicorn python-multipart
	$(PIP) freeze > server/requirements.txt

setup-frontend:
	@echo "Instalando dependencias de Svelte..."
	$(NPM) install

dev:
	@make -j 2 dev-backend dev-frontend

dev-backend:
	@echo "Iniciando FastAPI desde Conda..."
	cd server && $(UVICORN) main:app --reload --port 8000

dev-frontend:
	@echo "Iniciando SvelteKit..."
	$(NPM) run dev -- --open --port 5173