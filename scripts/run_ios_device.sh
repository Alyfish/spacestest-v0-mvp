#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="${ROOT_DIR}/ios-frontend"

DEVICE_ID="${1:-}"
if [[ -z "${DEVICE_ID}" ]]; then
  echo "Usage: $0 <flutter-device-id>"
  echo "Find your device id with: flutter devices"
  exit 1
fi

MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [[ -z "${MAC_IP}" ]]; then
  MAC_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

if [[ -z "${MAC_IP}" ]]; then
  echo "Could not resolve Mac LAN IP from en0/en1."
  echo "Connect to Wi-Fi and retry."
  exit 1
fi

API_BASE_URL="http://${MAC_IP}:8000/api"
echo "Device: ${DEVICE_ID}"
echo "API_BASE_URL: ${API_BASE_URL}"

cd "${IOS_DIR}"
flutter run -d "${DEVICE_ID}" --dart-define="API_BASE_URL=${API_BASE_URL}"
