#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/instance/run}"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: not running (no pid file)."
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    rm -f "${pid_file}"
    echo "${name}: pid file was empty; cleaned up."
    return 0
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "Stopping ${name} (pid ${pid})..."
    kill "${pid}" >/dev/null 2>&1 || true

    # Give it a moment to exit.
    for _ in {1..20}; do
      if ! kill -0 "${pid}" >/dev/null 2>&1; then
        break
      fi
      sleep 0.2
    done

    if kill -0 "${pid}" >/dev/null 2>&1; then
      echo "${name} still running; sending SIGKILL."
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  else
    echo "${name}: pid ${pid} not running; removing stale pid file."
  fi

  rm -f "${pid_file}"
}

stop_pid_file "backend" "${BACKEND_PID_FILE}"
stop_pid_file "frontend" "${FRONTEND_PID_FILE}"

echo "Done."

