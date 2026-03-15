#!/bin/bash
# Initialize database: run migrations and seed default sources

set -e

echo "=== AI Newsletter Service — DB Init ==="

cd "$(dirname "$0")/../backend"

echo "1. Running Alembic migrations..."
DATABASE_SYNC_URL="${DATABASE_SYNC_URL:-postgresql://aitracker:aitracker_secret@localhost:5432/aitracker}" \
  python -m alembic upgrade head

echo "2. Seeding default sources..."
python scripts/seed_sources.py

echo "Done!"
