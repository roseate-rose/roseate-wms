#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-5001}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"

CONFIRM="${CONFIRM:-0}"

find_listeners() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    echo "ERROR: lsof is required to find port listeners." >&2
    return 2
  fi

  # Print PIDs (one per line). Empty if none.
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | sort -u || true
}

describe_pid() {
  local pid="$1"
  if command -v ps >/dev/null 2>&1; then
    ps -p "${pid}" -o pid=,command= 2>/dev/null || true
  else
    echo "${pid}"
  fi
}

kill_pids() {
  local label="$1"
  shift || true
  local pids=("$@")

  if [[ "${#pids[@]}" -eq 0 ]]; then
    echo "${label}: no listeners"
    return 0
  fi

  echo "${label}:"
  for pid in "${pids[@]}"; do
    describe_pid "${pid}"
  done

  if [[ "${CONFIRM}" != "1" ]]; then
    echo
    echo "Refusing to kill without explicit confirmation."
    echo "Re-run with:"
    echo "  CONFIRM=1 $0"
    return 1
  fi

  echo "Sending SIGTERM..."
  for pid in "${pids[@]}"; do
    kill "${pid}" >/dev/null 2>&1 || true
  done

  sleep 0.8

  echo "Sending SIGKILL to remaining..."
  for pid in "${pids[@]}"; do
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  done
}

echo "Checking port conflicts (keeping fixed ports for webtest compatibility)..."
echo "  backend port:  ${BACKEND_PORT}"
echo "  frontend port: ${FRONTEND_PORT}"
echo

backend_pids=()
while IFS= read -r pid; do
  [[ -n "${pid}" ]] && backend_pids+=("${pid}")
done < <(find_listeners "${BACKEND_PORT}")

frontend_pids=()
while IFS= read -r pid; do
  [[ -n "${pid}" ]] && frontend_pids+=("${pid}")
done < <(find_listeners "${FRONTEND_PORT}")

if [[ "${#backend_pids[@]}" -gt 0 ]]; then
  kill_pids "Backend port ${BACKEND_PORT} listeners" "${backend_pids[@]}"
else
  kill_pids "Backend port ${BACKEND_PORT} listeners"
fi

if [[ "${#frontend_pids[@]}" -gt 0 ]]; then
  kill_pids "Frontend port ${FRONTEND_PORT} listeners" "${frontend_pids[@]}"
else
  kill_pids "Frontend port ${FRONTEND_PORT} listeners"
fi

echo
echo "Done. You can now run:"
echo "  ./scripts/local_test_up.sh"
