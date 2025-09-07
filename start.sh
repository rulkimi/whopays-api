#!/bin/sh

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
