CONDA_ENV_PATH = $(shell conda info --base)/envs/doc
PYTHON = $(CONDA_ENV_PATH)/bin/python
PIP = $(CONDA_ENV_PATH)/bin/pip
UVICORN = $(CONDA_ENV_PATH)/bin/uvicorn
NPM = npm --prefix client

.PHONY: setup-backend setup-frontend setup dev help

help:
	@echo "Commands:"
	@echo "  make setup          - Install dependencies backend and frontend"
	@echo "  make dev            - Run both servers (parallel)"

setup: setup-backend setup-frontend

setup-backend:
	@echo "Installing dependencies Python in Conda enviroment..."
	cd server && pip install -r requirements.txt

setup-frontend:
	@echo "Installing dependencies Svelte..."
	npm install

dev:
	@make -j 2 dev-backend dev-frontend

dev-backend:
	@echo "Initialize FastAPI since Conda..."
	cd server && $(UVICORN) main:app --reload --port 8300

dev-frontend:
	@echo "Initialize SvelteKit..."
	$(NPM) run dev -- --open --port 5173