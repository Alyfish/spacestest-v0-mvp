#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="${ROOT_DIR}/ios-frontend"
BACKEND_ENV_FILE="${ROOT_DIR}/backend/.env"

API_BASE_URL_ENV="${API_BASE_URL-}"
RC_API_KEY_ENV="${RC_API_KEY-}"
REVENUECAT_PUBLIC_KEY_ENV="${REVENUECAT_PUBLIC_KEY-}"

if [[ -f "${BACKEND_ENV_FILE}" ]]; then
  if [[ -z "${API_BASE_URL_ENV}" || ( -z "${RC_API_KEY_ENV}" && -z "${REVENUECAT_PUBLIC_KEY_ENV}" ) ]]; then
    set -a
    source "${BACKEND_ENV_FILE}"
    set +a
  fi
fi

API_BASE_URL="${API_BASE_URL_ENV:-${API_BASE_URL:-}}"
RC_API_KEY="${RC_API_KEY_ENV:-${RC_API_KEY:-${REVENUECAT_PUBLIC_KEY_ENV:-${REVENUECAT_PUBLIC_KEY:-}}}}"

if [[ $# -ge 1 ]]; then
  API_BASE_URL="$1"
fi
if [[ $# -ge 2 ]]; then
  RC_API_KEY="$2"
fi

EXTRA_ARGS=()
if [[ $# -gt 2 ]]; then
  EXTRA_ARGS=("${@:3}")
fi

if [[ -z "${API_BASE_URL}" || -z "${RC_API_KEY}" ]]; then
  echo "Usage: $0 <api_base_url> <rc_api_key> [extra flutter build args...]"
  echo "       Values can come from env vars API_BASE_URL and RC_API_KEY/REVENUECAT_PUBLIC_KEY."
  echo "       backend/.env is also checked for local development defaults."
  exit 1
fi

echo "Building iOS release with explicit API and RevenueCat defines..."
echo "API_BASE_URL: ${API_BASE_URL}"
echo "RC_API_KEY: [set]"

cd "${IOS_DIR}"
flutter build ios --release \
  --dart-define="API_BASE_URL=${API_BASE_URL}" \
  --dart-define="RC_API_KEY=${RC_API_KEY}" \
  "${EXTRA_ARGS[@]}"
