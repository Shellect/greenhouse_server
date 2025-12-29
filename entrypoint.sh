#!/bin/bash
set -e

echo "🌱 Running database migrations..."
alembic upgrade head

echo "🌱 Greenhouse Server starting"
echo "🍓 Strawberry optimal temp: 18.0-25.0°C"
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --no-access-log

