.PHONY: help dev prod build build-backend build-frontend up down logs logs-backend logs-frontend shell-backend shell-frontend stop restart clean env-setup

help:
	@echo "DentAI Docker Commands"
	@echo "====================="
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Start development environment (SQLite, hot reload)"
	@echo "  make dev-logs         - Show development logs"
	@echo "  make dev-stop         - Stop development environment"
	@echo "  make dev-clean        - Clean development containers and volumes"
	@echo ""
	@echo "Production:"
	@echo "  make prod             - Start production environment (PostgreSQL)"
	@echo "  make prod-logs        - Show production logs"
	@echo "  make prod-stop        - Stop production environment"
	@echo ""
	@echo "PostgreSQL (optional):"
	@echo "  make postgres         - Start with PostgreSQL database"
	@echo "  make postgres-stop    - Stop PostgreSQL"
	@echo "  make adminer          - Start Adminer for database management"
	@echo ""
	@echo "Building:"
	@echo "  make build            - Build all Docker images"
	@echo "  make build-backend    - Build backend image only"
	@echo "  make build-frontend   - Build frontend image only"
	@echo ""
	@echo "Utilities:"
	@echo "  make shell-backend    - Access backend container shell"
	@echo "  make shell-frontend   - Access frontend container shell"
	@echo "  make env-setup        - Create .env from .env.example"
	@echo "  make clean            - Remove all containers and volumes"
	@echo "  make status           - Show container status"
	@echo ""
	@echo "Note: Compose files live at repo root and Dockerfiles live in docker/"

# Development targets
dev: env-check
	@echo "Starting DentAI development environment..."
	docker-compose -f docker-compose.yml --profile dev up -d

dev-logs:
	docker-compose -f docker-compose.yml logs -f

dev-stop:
	@echo "Stopping development environment..."
	docker-compose -f docker-compose.yml --profile dev down

dev-clean:
	@echo "Cleaning up development environment..."
	docker-compose -f docker-compose.yml --profile dev down -v
	rm -rf db/runtime/*.db

# Production targets
prod: env-check
	@echo "Starting DentAI production environment..."
	docker-compose -f docker-compose.yml --profile prod --profile postgres up -d

prod-logs:
	docker-compose -f docker-compose.yml logs -f

prod-stop:
	@echo "Stopping production environment..."
	docker-compose -f docker-compose.yml --profile prod --profile postgres down

# PostgreSQL targets
postgres: env-check
	@echo "Starting with PostgreSQL..."
	docker-compose -f docker-compose.yml --profile postgres up -d

postgres-stop:
	docker-compose -f docker-compose.yml --profile postgres down

adminer:
	@echo "Adminer available at http://localhost:8080"
	@echo "Server: postgres"
	docker-compose -f docker-compose.yml up -d adminer

# Build targets
build: build-backend build-frontend
	@echo "All images built successfully!"

build-backend:
	@echo "Building backend image..."
	docker-compose -f docker-compose.yml build backend

build-frontend:
	@echo "Building frontend image..."
	docker-compose -f docker-compose.yml build frontend

# Shell access
shell-backend:
	docker-compose -f docker-compose.yml exec backend /bin/bash

shell-frontend:
	docker-compose -f docker-compose.yml exec frontend /bin/sh

# Utility targets
env-check:
	@if [ ! -f .env ]; then \
		echo "Missing .env file. Creating from .env.example..."; \
		cp .env.example .env; \
		echo "Created .env file. Please update with your actual values."; \
		echo "Key variables to update:"; \
		echo "  - DENTAI_SECRET_KEY"; \
		echo "  - GEMINI_API_KEY"; \
		echo "  - HUGGINGFACE_API_KEY"; \
	fi

env-setup:
	@echo "Creating .env from .env.example..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env - please update with your actual values"; \
	else \
		echo ".env already exists, skipping"; \
	fi

status:
	@echo "Container Status:"
	docker-compose -f docker-compose.yml ps

logs:
	docker-compose -f docker-compose.yml logs -f

logs-backend:
	docker-compose -f docker-compose.yml logs -f backend

logs-frontend:
	docker-compose -f docker-compose.yml logs -f frontend

stop:
	docker-compose -f docker-compose.yml down

restart:
	docker-compose -f docker-compose.yml restart

clean:
	@echo "Removing all containers and volumes..."
	docker-compose -f docker-compose.yml down -v
	docker-compose -f docker-compose.yml --profile postgres down -v
	docker-compose -f docker-compose.yml --profile prod down -v
	rm -rf db/runtime/*.db
	@echo "Clean complete!"

# Health checks
health:
	@echo "Checking service health..."
	@docker-compose -f docker-compose.yml ps
	@echo ""
	@echo "Backend API docs:"
	@curl -s http://localhost:8000/docs | grep -q "title" && echo "✓ Backend healthy" || echo "✗ Backend unhealthy"
	@echo "Frontend:"
	@curl -s http://localhost:3000 | head -1 | grep -q "html" && echo "✓ Frontend healthy" || echo "✗ Frontend unhealthy"
