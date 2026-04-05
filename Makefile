# =========================
# HyphaGraph Makefile
# =========================

COMPOSE_LOCAL = docker compose -f docker-compose.local.yml
PROJECT = hyphagraph
COMPOSE_REMOTE_DEV = docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml
COMPOSE_PROD = docker compose -f docker-compose.prod.yml

.DEFAULT_GOAL := help

## -------------------------
## Core lifecycle
## -------------------------

.PHONY: up
up: ## Start the full dev stack (Caddy, API, DB, Frontend)
	$(COMPOSE_LOCAL) up -d

.PHONY: dev-check
dev-check: ## Verify the local dev stack through Caddy using a real proxied API route
	@curl -sf http://localhost/api/entities/filter-options > /dev/null \
		&& echo "Caddy proxied API check passed" \
		|| (echo "Caddy proxied API check FAILED" && exit 1)

.PHONY: remote-dev-up
remote-dev-up: ## Start the remote development stack (requires .env)
	@test -f .env || (echo "Missing .env (copy from .env.example)" && exit 1)
	$(COMPOSE_REMOTE_DEV) up -d --build

.PHONY: down
down: ## Stop the stack
	$(COMPOSE_LOCAL) down

.PHONY: remote-dev-down
remote-dev-down: ## Stop the remote development stack
	$(COMPOSE_REMOTE_DEV) down

.PHONY: restart
restart: ## Restart the stack
	$(COMPOSE_LOCAL) down
	$(COMPOSE_LOCAL) up -d

.PHONY: build
build: ## Build all images
	$(COMPOSE_LOCAL) build

.PHONY: rebuild
rebuild: ## Rebuild images without cache
	$(COMPOSE_LOCAL) build --no-cache

## -------------------------
## Logs & status
## -------------------------

.PHONY: ps
ps: ## Show running containers
	$(COMPOSE_LOCAL) ps

.PHONY: logs
logs: ## Follow logs (all services)
	$(COMPOSE_LOCAL) logs -f

.PHONY: remote-dev-logs
remote-dev-logs: ## Follow logs for the remote development stack
	$(COMPOSE_REMOTE_DEV) logs -f

.PHONY: logs-api
logs-api: ## Follow API logs
	$(COMPOSE_LOCAL) logs -f api

.PHONY: logs-web
logs-web: ## Follow frontend logs
	$(COMPOSE_LOCAL) logs -f web

.PHONY: logs-db
logs-db: ## Follow database logs
	$(COMPOSE_LOCAL) logs -f db

.PHONY: logs-caddy
logs-caddy: ## Follow Caddy logs
	$(COMPOSE_LOCAL) logs -f caddy

## -------------------------
## Database utilities
## -------------------------

.PHONY: db-shell
db-shell: ## Open a psql shell inside the database container
	$(COMPOSE_LOCAL) exec db sh -c 'psql -U $$POSTGRES_USER $$POSTGRES_DB'

.PHONY: db-dump
db-dump: ## Dump the database to ./backups/hyphagraph.sql
	mkdir -p backups
	$(COMPOSE_LOCAL) exec -T db sh -c 'pg_dump -U $$POSTGRES_USER $$POSTGRES_DB' > backups/$(PROJECT).sql
	@echo "Database dumped to backups/$(PROJECT).sql"

.PHONY: db-restore
db-restore: ## Restore the database from ./backups/hyphagraph.sql
	cat backups/$(PROJECT).sql | $(COMPOSE_LOCAL) exec -T db sh -c 'psql -U $$POSTGRES_USER $$POSTGRES_DB'
	@echo "Database restored from backups/$(PROJECT).sql"

.PHONY: db-reset
db-reset: ## Drop and recreate the database (DANGEROUS)
	$(COMPOSE_LOCAL) exec db sh -c 'dropdb -U $$POSTGRES_USER $$POSTGRES_DB' || true
	$(COMPOSE_LOCAL) exec db sh -c 'createdb -U $$POSTGRES_USER $$POSTGRES_DB'
	@echo "Database reset"

## -------------------------
## Backend helpers
## -------------------------

.PHONY: api-shell
api-shell: ## Open a shell inside the API container
	$(COMPOSE_LOCAL) exec api bash

.PHONY: api-tests
api-tests: ## Run backend tests
	$(COMPOSE_LOCAL) exec api pytest

.PHONY: remote-dev-migrate
remote-dev-migrate: ## Apply Alembic migrations on the remote development stack
	$(COMPOSE_REMOTE_DEV) exec api alembic upgrade head

## -------------------------
## Domain-level scripts
## -------------------------

.PHONY: extract
extract: ## Run LLM-assisted relation extraction
	$(COMPOSE_LOCAL) exec api python scripts/extract_relations.py

.PHONY: recompute
recompute: ## Recompute all inferences deterministically
	$(COMPOSE_LOCAL) exec api python scripts/recompute_inferences.py

## -------------------------
## Self-hosting
## -------------------------

.PHONY: prod-setup
prod-setup: ## Interactive setup wizard (run once on a fresh server)
	bash scripts/setup-self-host.sh

.PHONY: prod-up
prod-up: ## Start the production stack
	$(COMPOSE_PROD) up -d

.PHONY: prod-down
prod-down: ## Stop the production stack
	$(COMPOSE_PROD) down

.PHONY: prod-logs
prod-logs: ## Follow logs for the production stack
	$(COMPOSE_PROD) logs -f

.PHONY: prod-update
prod-update: ## Back up DB, pull new images, and restart production
	@echo "Backing up database before update..."
	@mkdir -p backups
	$(COMPOSE_PROD) exec -T db sh -c 'pg_dump -U $$POSTGRES_USER $$POSTGRES_DB' > backups/pre-update-$$(date +%Y%m%d%H%M%S).sql
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d
	@echo "Update complete."

.PHONY: prod-backup
prod-backup: ## Dump the production database to ./backups/
	mkdir -p backups
	$(COMPOSE_PROD) exec -T db sh -c 'pg_dump -U $$POSTGRES_USER $$POSTGRES_DB' > backups/hyphagraph-$$(date +%Y%m%d%H%M%S).sql
	@echo "Backup saved to backups/"

.PHONY: prod-check
prod-check: ## Verify the production deployment is healthy
	@$(COMPOSE_PROD) exec api curl -sf http://localhost:8000/health \
		&& echo "API is healthy" \
		|| (echo "API health check FAILED" && exit 1)
	@$(COMPOSE_PROD) exec web wget -qO- http://localhost:80/ > /dev/null \
		&& echo "Web is healthy" \
		|| (echo "Web health check FAILED" && exit 1)

## -------------------------
## Cleanup
## -------------------------

.PHONY: clean
clean: ## Stop containers and remove volumes (DATA LOSS)
	$(COMPOSE_LOCAL) down -v

## -------------------------
## Help
## -------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
