#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI on IPv6..."
uvicorn main:app --host :: --port ${PORT}
