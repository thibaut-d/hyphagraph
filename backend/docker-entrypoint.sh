#!/bin/sh
set -eu

echo "Applying database migrations..."
uv run alembic upgrade head

echo "Bootstrapping admin user..."
uv run python bootstrap_admin.py

echo "Starting API server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
