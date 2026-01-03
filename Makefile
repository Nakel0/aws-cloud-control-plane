# CloudGuard Makefile
# Convenience commands for development

.PHONY: help install start stop test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Dependencies installed"

start: ## Start all services with Docker Compose
	@echo "Starting CloudGuard..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/api/docs"

stop: ## Stop all services
	@echo "Stopping CloudGuard..."
	docker-compose down
	@echo "✅ Services stopped"

logs: ## View logs from all services
	docker-compose logs -f

restart: ## Restart all services
	@make stop
	@make start

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "✅ Tests completed"

test-backend: ## Run backend tests only
	cd backend && pytest -v

test-frontend: ## Run frontend tests only
	cd frontend && npm test

lint: ## Run linters
	@echo "Linting backend..."
	cd backend && black app/ && flake8 app/
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "✅ Linting completed"

format: ## Format code
	@echo "Formatting backend..."
	cd backend && black app/
	@echo "Formatting frontend..."
	cd frontend && npm run lint -- --fix
	@echo "✅ Code formatted"

db-init: ## Initialize database
	docker-compose exec backend python -c "from app.core.database import init_db; init_db()"
	@echo "✅ Database initialized"

db-migrate: ## Run database migrations
	cd backend && alembic upgrade head
	@echo "✅ Migrations applied"

db-seed: ## Seed database with sample data
	docker-compose exec backend python scripts/seed_data.py
	@echo "✅ Database seeded"

clean: ## Clean up generated files and containers
	@echo "Cleaning up..."
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup completed"

build: ## Build Docker images
	docker-compose build
	@echo "✅ Images built"

ps: ## Show running containers
	docker-compose ps

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U cloudguard

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

dev-backend: ## Run backend in development mode (without Docker)
	cd backend && uvicorn app.main:app --reload

dev-frontend: ## Run frontend in development mode (without Docker)
	cd frontend && npm run dev

dev-worker: ## Run Celery worker (without Docker)
	cd backend && celery -A app.tasks worker --loglevel=info

docs: ## Generate API documentation
	@echo "API documentation available at http://localhost:8000/api/docs"

update: ## Update all dependencies
	@echo "Updating backend dependencies..."
	cd backend && pip install --upgrade -r requirements.txt
	@echo "Updating frontend dependencies..."
	cd frontend && npm update
	@echo "✅ Dependencies updated"
