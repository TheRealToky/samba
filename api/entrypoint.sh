#!/bin/sh
set -e

# With several API replicas sharing one database, only one may run migrations —
# concurrent `alembic upgrade head` races on the version table. The designated
# migrator (web-01) leaves this unset; every other server sets RUN_MIGRATIONS=false.
if [ "${RUN_MIGRATIONS:-true}" = "false" ]; then
    echo "[entrypoint] RUN_MIGRATIONS=false -- skipping migrations"
else
    echo "[entrypoint] waiting for database + applying migrations..."
    alembic upgrade head
fi

echo "[entrypoint] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
