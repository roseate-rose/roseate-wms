#!/usr/bin/env bash

set -euo pipefail

SCREEN_NAME="${SCREEN_NAME:-roseate-wms}"

if screen -list | grep -q "[.]${SCREEN_NAME}[[:space:]]"; then
  echo "Stopping screen session '${SCREEN_NAME}'..."
  screen -S "${SCREEN_NAME}" -X quit
  echo "Stopped."
else
  echo "screen session '${SCREEN_NAME}' not found."
fi
