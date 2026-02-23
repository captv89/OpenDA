#!/bin/sh
set -e

echo "========================================"
echo " OpenDA Backend — startup"
echo " $(date -u)"
echo "========================================"

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

echo "[entrypoint] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
