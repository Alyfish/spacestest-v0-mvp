#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="${ROOT_DIR}/ios-frontend"
BACKEND_ENV_FILE="${ROOT_DIR}/backend/.env"

DEVICE_ID="${1:-}"
RC_API_KEY_ARG="${2:-}"
API_BASE_URL_ARG="${3:-}"

RC_API_KEY_ENV="${RC_API_KEY-}"
REVENUECAT_PUBLIC_KEY_ENV="${REVENUECAT_PUBLIC_KEY-}"
API_BASE_URL_ENV="${API_BASE_URL-}"
DEV_IAP_ENABLED_ENV="${DEV_IAP_ENABLED-}"

if [[ -f "${BACKEND_ENV_FILE}" ]]; then
  if [[ -z "${RC_API_KEY_ENV}" && -z "${REVENUECAT_PUBLIC_KEY_ENV}" ]] || \
     [[ -z "${API_BASE_URL_ENV}" ]] || \
     [[ -z "${DEV_IAP_ENABLED_ENV}" ]]; then
    set -a
    # Source backend defaults for local development convenience.
    source "${BACKEND_ENV_FILE}"
    set +a
  fi
fi

RC_API_KEY="${RC_API_KEY_ARG:-${RC_API_KEY_ENV:-${RC_API_KEY:-${REVENUECAT_PUBLIC_KEY_ENV:-${REVENUECAT_PUBLIC_KEY:-}}}}}"
API_BASE_URL="${API_BASE_URL_ARG:-${API_BASE_URL_ENV:-${API_BASE_URL:-}}}"
DEV_IAP_ENABLED_DART_DEFINE="${DEV_IAP_ENABLED_ENV:-${DEV_IAP_ENABLED:-false}}"

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ -z "${DEVICE_ID}" ]]; then
  echo "Usage: $0 <flutter-device-id> [rc_api_key] [api_base_url]"
  echo "       RC key can come from arg 2, RC_API_KEY, REVENUECAT_PUBLIC_KEY, or backend/.env."
  echo "       API base URL can also come from env var API_BASE_URL."
  echo "Find your device id with: flutter devices"
  exit 1
fi

if [[ -z "${RC_API_KEY}" ]] && ! is_truthy "${DEV_IAP_ENABLED_DART_DEFINE}"; then
  echo "RevenueCat public key is required when DEV_IAP_ENABLED is false."
  echo "Provide arg 2, export RC_API_KEY/REVENUECAT_PUBLIC_KEY, or set REVENUECAT_PUBLIC_KEY in backend/.env."
  exit 1
fi

if [[ -z "${API_BASE_URL}" ]]; then
  MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "${MAC_IP}" ]]; then
    MAC_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi

  if [[ -z "${MAC_IP}" ]]; then
    echo "Could not resolve Mac LAN IP from en0/en1."
    echo "Connect to Wi-Fi and retry, or pass API base URL explicitly."
    exit 1
  fi

  API_BASE_URL="http://${MAC_IP}:8000/api"
fi

echo "Device: ${DEVICE_ID}"
echo "API_BASE_URL: ${API_BASE_URL}"
if [[ -n "${RC_API_KEY}" ]]; then
  echo "RC_API_KEY: [set]"
else
  echo "RC_API_KEY: [missing - mock mode expected]"
fi
echo "DEV_IAP_ENABLED (Flutter): ${DEV_IAP_ENABLED_DART_DEFINE}"

cd "${IOS_DIR}"
flutter run -d "${DEVICE_ID}" \
  --dart-define="API_BASE_URL=${API_BASE_URL}" \
  --dart-define="RC_API_KEY=${RC_API_KEY}" \
  --dart-define="DEV_IAP_ENABLED=${DEV_IAP_ENABLED_DART_DEFINE}"
