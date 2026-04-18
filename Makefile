# =============================================================================
# RAZE Enterprise AI OS — Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

COMPOSE      := docker compose
BACKEND_SVC  := backend
DB_SVC       := postgres

.DEFAULT_GOAL := help

.PHONY: help setup up down restart logs logs-backend logs-frontend logs-nginx \
        migrate migrate-down shell-backend shell-db shell-redis \
        backup restore ps status build pull clean prune \
        test health generate-secrets setup-admin test-chat

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@printf "\n\033[1;36mRAZE Enterprise AI OS\033[0m — available targets:\n\n"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[32m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\n"

# ── Setup ─────────────────────────────────────────────────────────────────────
setup: ## First-time setup: copy .env, create init SQL, start services
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		printf "\033[33m[setup]\033[0m Copied .env.example → .env. Edit .env before continuing.\n"; \
	else \
		printf "\033[32m[setup]\033[0m .env already exists — skipping copy.\n"; \
	fi
	@mkdir -p scripts nginx
	@if [ ! -f scripts/init-db.sql ]; then \
		printf "CREATE EXTENSION IF NOT EXISTS vector;\nCREATE EXTENSION IF NOT EXISTS pg_trgm;\nCREATE EXTENSION IF NOT EXISTS btree_gin;\n" > scripts/init-db.sql; \
		printf "\033[32m[setup]\033[0m Created scripts/init-db.sql\n"; \
	fi
	@printf "\033[32m[setup]\033[0m Run 'make up' to start all services.\n"

# ── Lifecycle ─────────────────────────────────────────────────────────────────
up: ## Start all services (detached)
	$(COMPOSE) up -d --remove-orphans

down: ## Stop and remove all containers
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

restart-backend: ## Restart only the backend service
	$(COMPOSE) restart $(BACKEND_SVC)

restart-frontend: ## Restart only the frontend service
	$(COMPOSE) restart frontend

build: ## Build/rebuild all images
	$(COMPOSE) build --no-cache

pull: ## Pull latest base images
	$(COMPOSE) pull

# ── Logs ──────────────────────────────────────────────────────────────────────
logs: ## Tail logs for all services (Ctrl+C to exit)
	$(COMPOSE) logs -f --tail=100

logs-backend: ## Tail backend logs
	$(COMPOSE) logs -f --tail=100 $(BACKEND_SVC)

logs-frontend: ## Tail frontend logs
	$(COMPOSE) logs -f --tail=100 frontend

logs-nginx: ## Tail nginx logs
	$(COMPOSE) logs -f --tail=100 nginx

logs-db: ## Tail postgres logs
	$(COMPOSE) logs -f --tail=100 $(DB_SVC)

# ── Database Migrations ───────────────────────────────────────────────────────
migrate: ## Run Alembic migrations (upgrade head)
	$(COMPOSE) exec $(BACKEND_SVC) alembic upgrade head

migrate-down: ## Rollback one Alembic migration step
	$(COMPOSE) exec $(BACKEND_SVC) alembic downgrade -1

migrate-history: ## Show Alembic migration history
	$(COMPOSE) exec $(BACKEND_SVC) alembic history --verbose

migrate-current: ## Show current Alembic revision
	$(COMPOSE) exec $(BACKEND_SVC) alembic current

migrate-create: ## Create new migration: make migrate-create MSG="add users table"
	$(COMPOSE) exec $(BACKEND_SVC) alembic revision --autogenerate -m "$(MSG)"

# ── Interactive Shells ────────────────────────────────────────────────────────
shell-backend: ## Open bash shell in backend container
	$(COMPOSE) exec $(BACKEND_SVC) /bin/bash

shell-db: ## Open psql shell in postgres container
	$(COMPOSE) exec $(DB_SVC) psql -U $${POSTGRES_USER:-raze} -d $${POSTGRES_DB:-raze}

shell-redis: ## Open redis-cli shell in redis container
	$(COMPOSE) exec redis redis-cli -a $${REDIS_PASSWORD}

shell-minio: ## Open shell in minio container
	$(COMPOSE) exec minio /bin/sh

# ── Backup & Restore ──────────────────────────────────────────────────────────
backup: ## Dump PostgreSQL database to ./backups/
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	$(COMPOSE) exec -T $(DB_SVC) pg_dump \
		-U $${POSTGRES_USER:-raze} \
		-d $${POSTGRES_DB:-raze} \
		--no-password \
		--format=custom \
		--compress=9 \
	> backups/raze_$$TIMESTAMP.pgdump && \
	printf "\033[32m[backup]\033[0m Saved to backups/raze_$$TIMESTAMP.pgdump\n"

restore: ## Restore from a dump file: make restore FILE=backups/raze_YYYYMMDD_HHMMSS.pgdump
	@if [ -z "$(FILE)" ]; then \
		printf "\033[31m[error]\033[0m Specify dump file: make restore FILE=backups/raze_*.pgdump\n"; exit 1; \
	fi
	$(COMPOSE) exec -T $(DB_SVC) pg_restore \
		-U $${POSTGRES_USER:-raze} \
		-d $${POSTGRES_DB:-raze} \
		--no-password \
		--clean \
		--if-exists \
		< $(FILE)
	@printf "\033[32m[restore]\033[0m Database restored from $(FILE)\n"

# ── Status & Cleanup ──────────────────────────────────────────────────────────
ps: ## Show running containers and their status
	$(COMPOSE) ps

status: ps ## Alias for ps

clean: ## Remove stopped containers, unused networks, and dangling images
	docker system prune -f

prune: ## Remove ALL unused Docker resources including volumes (DESTRUCTIVE)
	@printf "\033[31mWARNING: This will delete all unused Docker volumes. Are you sure? [y/N] \033[0m" && \
	read ans && [ $${ans:-N} = y ] && docker system prune -af --volumes || printf "Aborted.\n"

# ── Testing & Verification ───────────────────────────────────────────────────────
test: ## Run comprehensive deployment tests
	@bash scripts/test-deployment.sh

health: ## Quick health check of all services
	@echo "Checking services..."
	@docker compose ps
	@echo ""
	@echo "Backend: $$(curl -s http://localhost/health || echo 'DOWN')"
	@echo "Frontend: $$(curl -s http://localhost/ | grep -q html && echo 'UP' || echo 'DOWN')"
	@echo "Postgres: $$(docker compose exec -T postgres pg_isready -U raze -d raze 2>/dev/null && echo 'UP' || echo 'DOWN')"
	@echo "Redis: $$(docker compose exec -T redis redis-cli ping 2>/dev/null && echo 'UP' || echo 'DOWN')"

# ── Configuration ─────────────────────────────────────────────────────────────────
generate-secrets: ## Generate secure credentials for .env
	@bash scripts/generate-secrets.sh

setup-admin: ## Create default admin user and initial configurations
	@bash scripts/setup-admin.sh

# ── Testing Chat ──────────────────────────────────────────────────────────────────
test-chat: ## Send test message to chat API (requires TOKEN env var)
	@if [ -z "$$TOKEN" ]; then \
		printf "\033[31m[error]\033[0m Set TOKEN environment variable\n"; \
		printf "Usage: TOKEN=<jwt-token> make test-chat\n"; \
		exit 1; \
	fi
	@printf "\033[32m[chat test]\033[0m Sending test message...\n"
	@curl -X POST http://localhost/api/v1/chat/message \
		-H "Authorization: Bearer $$TOKEN" \
		-H "Content-Type: application/json" \
		-d '{"message":"Hello! Tell me what you can do.","use_knowledge":true,"use_memory":true}' \
		| jq .
	@printf "\033[32m[chat test]\033[0m Complete\n"
