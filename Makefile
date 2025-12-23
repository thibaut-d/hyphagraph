# =========================
# HyphaGraph Makefile
# =========================

COMPOSE = docker compose
PROJECT = hyphagraph

.DEFAULT_GOAL := help

## -------------------------
## Core lifecycle
## -------------------------

.PHONY: up
up: ## Start the full dev stack (Caddy, API, DB, Frontend)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart the stack
	$(COMPOSE) down
	$(COMPOSE) up -d

.PHONY: build
build: ## Build all images
	$(COMPOSE) build

.PHONY: rebuild
rebuild: ## Rebuild images without cache
	$(COMPOSE) build --no-cache

## -------------------------
## Logs & status
## -------------------------

.PHONY: ps
ps: ## Show running containers
	$(COMPOSE) ps

.PHONY: logs
logs: ## Follow logs (all services)
	$(COMPOSE) logs -f

.PHONY: logs-api
logs-api: ## Follow API logs
	$(COMPOSE) logs -f api

.PHONY: logs-web
logs-web: ## Follow frontend logs
	$(COMPOSE) logs -f web

.PHONY: logs-db
logs-db: ## Follow database logs
	$(COMPOSE) logs -f db

.PHONY: logs-caddy
logs-caddy: ## Follow Caddy logs
	$(COMPOSE) logs -f caddy

## -------------------------
## Database utilities
## -------------------------

.PHONY: db-shell
db-shell: ## Open a psql shell inside the database container
	$(COMPOSE) exec db psql -U $$POSTGRES_USER $$POSTGRES_DB

.PHONY: db-dump
db-dump: ## Dump the database to ./backups/hyphagraph.sql
	mkdir -p backups
	$(COMPOSE) exec -T db pg_dump -U $$POSTGRES_USER $$POSTGRES_DB > backups/$(PROJECT).sql
	@echo "Database dumped to backups/$(PROJECT).sql"

.PHONY: db-restore
db-restore: ## Restore the database from ./backups/hyphagraph.sql
	cat backups/$(PROJECT).sql | $(COMPOSE) exec -T db psql -U $$POSTGRES_USER $$POSTGRES_DB
	@echo "Database restored from backups/$(PROJECT).sql"

.PHONY: db-reset
db-reset: ## Drop and recreate the database (DANGEROUS)
	$(COMPOSE) exec db dropdb -U $$POSTGRES_USER $$POSTGRES_DB || true
	$(COMPOSE) exec db createdb -U $$POSTGRES_USER $$POSTGRES_DB
	@echo "Database reset"

## -------------------------
## Backend helpers
## -------------------------

.PHONY: api-shell
api-shell: ## Open a shell inside the API container
	$(COMPOSE) exec api bash

.PHONY: api-tests
api-tests: ## Run backend tests
	$(COMPOSE) exec api pytest

## -------------------------
## Domain-level scripts
## -------------------------

.PHONY: extract
extract: ## Run LLM-assisted relation extraction
	$(COMPOSE) exec api python scripts/extract_relations.py

.PHONY: recompute
recompute: ## Recompute all inferences deterministically
	$(COMPOSE) exec api python scripts/recompute_inferences.py

## -------------------------
## Cleanup
## -------------------------

.PHONY: clean
clean: ## Stop containers and remove volumes (DATA LOSS)
	$(COMPOSE) down -v

## -------------------------
## Help
## -------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'