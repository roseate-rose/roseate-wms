#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/instance/run}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
# Default ports here are optimized for "keep-alive local testing":
# - 5000 is sometimes occupied by other local services on macOS.
# - 5173 is often taken by another Vite project.
BACKEND_PORT="${BACKEND_PORT:-5001}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"

mkdir -p "${RUN_DIR}"

is_listening() {
  local host="$1"
  local port="$2"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

is_pid_running() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  kill -0 "${pid}" >/dev/null 2>&1
}

ensure_started_or_die() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"

  sleep 0.4
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" >/dev/null 2>&1; then
    echo "${name} failed to start."
    if [[ -f "${log_file}" ]]; then
      echo "Last logs (${log_file}):"
      tail -n 60 "${log_file}" || true
    fi
    exit 1
  fi
}

echo "Starting roseate-wms local test services..."
echo "  backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "  run dir:  ${RUN_DIR}"

if is_pid_running "${BACKEND_PID_FILE}"; then
  echo "Backend already running (pid $(cat "${BACKEND_PID_FILE}"))."
else
  if is_listening "${BACKEND_HOST}" "${BACKEND_PORT}"; then
    echo "Backend port ${BACKEND_PORT} is already in use."
    echo "We keep ports stable for cross-repo tooling (e.g. webtest)."
    echo "If the conflict is from another project, kill it first:"
    echo "  CONFIRM=1 ./scripts/local_test_kill_conflicts.sh"
    exit 1
  fi

  echo "Starting backend..."
  (
    cd "${ROOT_DIR}"
    export PYTHONDONTWRITEBYTECODE=1
    if python3 -m gunicorn --version >/dev/null 2>&1; then
      nohup python3 -m gunicorn \
        --bind "${BACKEND_HOST}:${BACKEND_PORT}" \
        --workers 1 \
        --threads 4 \
        --access-logfile - \
        --error-logfile - \
        backend.app:app \
        > "${RUN_DIR}/backend.log" 2>&1 &
    else
      nohup python3 backend/app.py --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" \
      > "${RUN_DIR}/backend.log" 2>&1 &
    fi
    echo $! > "${BACKEND_PID_FILE}"
  )
  echo "Backend started (pid $(cat "${BACKEND_PID_FILE}")). Logs: ${RUN_DIR}/backend.log"
  ensure_started_or_die "Backend" "${BACKEND_PID_FILE}" "${RUN_DIR}/backend.log"
fi

if is_pid_running "${FRONTEND_PID_FILE}"; then
  echo "Frontend already running (pid $(cat "${FRONTEND_PID_FILE}"))."
else
  if is_listening "${FRONTEND_HOST}" "${FRONTEND_PORT}"; then
    echo "Frontend port ${FRONTEND_PORT} is already in use."
    echo "We keep ports stable for cross-repo tooling (e.g. webtest)."
    echo "If the conflict is from another project, kill it first:"
    echo "  CONFIRM=1 ./scripts/local_test_kill_conflicts.sh"
    exit 1
  fi

  echo "Starting frontend..."
  (
    cd "${ROOT_DIR}/frontend"
    export VITE_API_PROXY_TARGET="http://${BACKEND_HOST}:${BACKEND_PORT}"
    nohup npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" --strictPort \
      > "${RUN_DIR}/frontend.log" 2>&1 &
    echo $! > "${FRONTEND_PID_FILE}"
  )
  echo "Frontend started (pid $(cat "${FRONTEND_PID_FILE}")). Logs: ${RUN_DIR}/frontend.log"
  ensure_started_or_die "Frontend" "${FRONTEND_PID_FILE}" "${RUN_DIR}/frontend.log"
fi

cat <<EOF

Status:
  Backend PID:  $(cat "${BACKEND_PID_FILE}" 2>/dev/null || echo "-")
  Frontend PID: $(cat "${FRONTEND_PID_FILE}" 2>/dev/null || echo "-")

Tips:
  - Stop:   ./scripts/local_test_down.sh
  - Status: ./scripts/local_test_status.sh
  - Logs:   tail -f ${RUN_DIR}/backend.log
           tail -f ${RUN_DIR}/frontend.log

EOF
