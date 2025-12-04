# TrustChain Makefile
# Common development commands
#
# Built with care by Kareem & Claude

.PHONY: help install test lint format docker-up docker-down clean

# Default target
help:
	@echo "TrustChain Development Commands"
	@echo "================================"
	@echo "make install     - Install dependencies"
	@echo "make test        - Run tests"
	@echo "make test-cov    - Run tests with coverage"
	@echo "make lint        - Run linters"
	@echo "make format      - Format code"
	@echo "make docker-up   - Start Docker containers"
	@echo "make docker-down - Stop Docker containers"
	@echo "make docker-dev  - Start in development mode"
	@echo "make clean       - Clean up cache files"
	@echo "make run         - Run development server"

# =============================================================================
# Development
# =============================================================================

install:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov httpx black ruff mypy

run:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-fast:
	pytest tests/ -v -x --tb=short

# =============================================================================
# Code Quality
# =============================================================================

lint:
	ruff check .
	black --check .
	mypy . --ignore-missing-imports || true

format:
	black .
	ruff check . --fix

# =============================================================================
# Docker
# =============================================================================

docker-up:
	docker-compose up -d
	@echo "TrustChain API running at http://localhost:8000"
	@echo "PostgreSQL running at localhost:5432"

docker-down:
	docker-compose down

docker-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f api

docker-shell:
	docker-compose exec api /bin/bash

# With optional services
docker-up-full:
	docker-compose --profile local-llm --profile with-cache up -d

# =============================================================================
# Database
# =============================================================================

db-migrate:
	@echo "Running database migrations..."
	# Add alembic commands when migrations are set up

db-reset:
	docker-compose down -v
	docker-compose up -d db
	@echo "Database reset complete"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleaned up cache files"
