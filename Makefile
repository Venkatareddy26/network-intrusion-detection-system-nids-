.PHONY: help install test lint format clean docker-build docker-up docker-down train

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean generated files"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start Docker containers"
	@echo "  make docker-down   - Stop Docker containers"
	@echo "  make train         - Train model"
	@echo "  make run-api       - Run API server"
	@echo "  make run-dashboard - Run dashboard"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -m "not slow"

lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ .mypy_cache .ruff_cache
	rm -rf build/ dist/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

train:
	python train_model.py

run-api:
	python -m uvicorn src.nids.api.main_v2:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	streamlit run src/nids/dashboard/app.py

security-scan:
	bandit -r src/ -f json -o bandit-report.json
	safety check

setup-env:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"

init-db:
	mkdir -p data models logs
	@echo "Directories created"
