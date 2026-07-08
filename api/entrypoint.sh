#!/bin/sh
set -e

echo "[entrypoint] waiting for database + applying migrations..."
alembic upgrade head

echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
