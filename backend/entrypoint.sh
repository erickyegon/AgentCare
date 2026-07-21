#!/usr/bin/env bash
# Container entrypoint: run migrations, then start the API.
# Table creation + synthetic seeding also happen on app startup (auto_init_db / auto_seed),
# but running Alembic here keeps the schema authoritative in production (PostgreSQL).
set -e

echo "[entrypoint] Applying database migrations…"
alembic upgrade head || echo "[entrypoint] Alembic upgrade skipped/failed (app will ensure schema on startup)."

echo "[entrypoint] Starting AgentCare API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-1}"
