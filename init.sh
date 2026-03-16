#!/bin/bash
# init.sh — start all services and verify baseline functionality
set -e

cd "$(dirname "$0")"

echo "=== Starting all Docker services ==="
docker compose up -d

echo "=== Waiting for backend to be healthy ==="
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend is up after ${i} attempts."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Backend did not become healthy in time."
    docker compose logs backend --tail=30
    exit 1
  fi
  sleep 2
done

echo ""
echo "=== Smoke Tests ==="

echo -n "Backend health check: "
HEALTH=$(curl -sf http://localhost:8000/health)
echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('status')=='ok', f'Expected ok, got {d}'; print('OK')"

echo -n "Sources endpoint: "
SOURCES=$(curl -sf http://localhost:8000/api/v1/sources/)
echo "$SOURCES" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Sources count: {len(d)}')"

echo -n "Dashboard summary: "
DASHBOARD=$(curl -sf http://localhost:8000/api/v1/dashboard/summary)
echo "$DASHBOARD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'articles_today={d.get(\"articles_today\",\"?\")} total_articles={d.get(\"total_articles\",\"?\")}')"

echo -n "Frontend status: "
FRONTEND_STATUS=$(curl -so /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo "unreachable")
echo "$FRONTEND_STATUS"

echo ""
echo "=== Docker containers status ==="
docker compose ps

echo ""
echo "=== init.sh complete ==="
