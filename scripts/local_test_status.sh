#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/instance/run}"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"

check_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: stopped"
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    echo "${name}: stopped (empty pid file)"
    return 0
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "${name}: running (pid ${pid})"
  else
    echo "${name}: stopped (stale pid ${pid})"
  fi
}

echo "roseate-wms local test service status"
echo "run dir: ${RUN_DIR}"
check_pid_file "backend" "${BACKEND_PID_FILE}"
check_pid_file "frontend" "${FRONTEND_PID_FILE}"

