#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <railway-domain-or-url>"
  echo "Example: $0 https://spaces-backend-production.up.railway.app"
  exit 1
fi

BASE="$1"
if [[ "${BASE}" != http*://* ]]; then
  BASE="https://${BASE}"
fi
BASE="${BASE%/}"

echo "Checking ${BASE}/health"
curl -fsS -i "${BASE}/health" >/tmp/railway_health.out
grep -q "200" /tmp/railway_health.out
echo "OK: /health"

echo "Checking ${BASE}/api/health"
curl -fsS -i "${BASE}/api/health" >/tmp/railway_api_health.out
grep -q "200" /tmp/railway_api_health.out
echo "OK: /api/health"

echo "Smoke check passed."
