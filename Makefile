# =============================================================
# ClientFinder AI Agent
# =============================================================
# AI-powered lead generation agent for freelance software developers
# Built with FastAPI + React + PostgreSQL + Redis + Celery
# =============================================================

.PHONY: help up down restart logs ps build rebuild pull \
        backend-shell frontend-shell postgres-shell redis-shell minio-shell \
        migrate makemigration seed createsuperuser test lint format clean \
        backup restore health

# ---------- Colors ----------
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

help: ## Show this help
	@echo "$(GREEN)ClientFinder AI Agent$(RESET) — available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(RESET) %s\n", $$1, $$2}'

# ---------- Core lifecycle ----------
up: ## Start all services
	docker compose up -d
	@echo "$(GREEN)✓ Services started$(RESET)"
	@make health

down: ## Stop all services
	docker compose down
	@echo "$(GREEN)✓ Services stopped$(RESET)"

restart: ## Restart all services
	docker compose restart
	@echo "$(GREEN)✓ Services restarted$(RESET)"

logs: ## Tail logs (use ctrl+c to exit)
	docker compose logs -f --tail=100

ps: ## List running services
	docker compose ps

# ---------- Build ----------
build: ## Build all images
	docker compose build
	@echo "$(GREEN)✓ Images built$(RESET)"

rebuild: ## Rebuild from scratch (no cache)
	docker compose build --no-cache
	@echo "$(GREEN)✓ Images rebuilt$(RESET)"

pull: ## Pull base images
	docker compose pull

# ---------- Shell access ----------
backend-shell: ## Open shell in backend container
	docker compose exec backend /bin/bash

frontend-shell: ## Open shell in frontend container
	docker compose exec frontend /bin/sh

postgres-shell: ## Open psql in postgres
	docker compose exec postgres psql -U $${POSTGRES_USER:-clientfinder} -d $${POSTGRES_DB:-clientfinder}

redis-shell: ## Open redis-cli
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD}

minio-shell: ## Open mc client (configure alias first via setup-minio)
	docker compose exec minio /bin/sh

# ---------- Database ----------
migrate: ## Apply all pending migrations
	docker compose exec backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations applied$(RESET)"

makemigration: ## Create new migration (usage: make makemigration msg="add users table")
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

seed: ## Seed initial data
	docker compose exec backend python -m scripts.seed_data

createsuperuser: ## Create admin user
	docker compose exec backend python -m scripts.create_admin

# ---------- Quality ----------
test: ## Run all tests
	docker compose exec backend pytest -v

lint: ## Run linting
	docker compose exec backend ruff check app
	docker compose exec frontend npm run lint

format: ## Auto-format code
	docker compose exec backend ruff format app
	docker compose exec frontend npm run format

# ---------- Health ----------
health: ## Check service health
	@echo "$(GREEN)Health check:$(RESET)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ---------- Backup ----------
backup: ## Manual backup
	./scripts/backup.sh

restore: ## Restore from backup file (usage: make restore file=backups/db_20240101.sql.gz.gpg)
	./scripts/restore.sh $(file)

# ---------- Cleanup ----------
clean: ## Stop services, remove volumes, prune images (DESTRUCTIVE)
	@echo "$(YELLOW)⚠ This will delete all data. Press Ctrl-C to abort.$(RESET)"
	@sleep 5
	docker compose down -v
	docker system prune -f
	@echo "$(GREEN)✓ Cleanup done$(RESET)"
