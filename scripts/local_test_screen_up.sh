#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/instance/run}"
SCREEN_NAME="${SCREEN_NAME:-roseate-wms}"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-5001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

mkdir -p "${RUN_DIR}"

if screen -list | grep -q "[.]${SCREEN_NAME}[[:space:]]"; then
  echo "screen session '${SCREEN_NAME}' already exists."
  echo "Attach: screen -r ${SCREEN_NAME}"
  exit 0
fi

echo "Starting detached screen session '${SCREEN_NAME}'..."
echo "  backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "  logs:     ${RUN_DIR}/backend.log, ${RUN_DIR}/frontend.log"

screen -S "${SCREEN_NAME}" -dm bash -lc "
  cd '${ROOT_DIR}' && \
  export PYTHONDONTWRITEBYTECODE=1 && \
  python3 backend/app.py --host '${BACKEND_HOST}' --port '${BACKEND_PORT}' 2>&1 | tee -a '${RUN_DIR}/backend.log'
"

screen -S "${SCREEN_NAME}" -X screen -t frontend bash -lc "
  cd '${ROOT_DIR}/frontend' && \
  export VITE_API_PROXY_TARGET='http://${BACKEND_HOST}:${BACKEND_PORT}' && \
  npm run dev -- --host '${FRONTEND_HOST}' --port '${FRONTEND_PORT}' --strictPort 2>&1 | tee -a '${RUN_DIR}/frontend.log'
"

cat <<EOF

Started.
  Attach: screen -r ${SCREEN_NAME}
  Stop:   ./scripts/local_test_screen_down.sh

EOF
