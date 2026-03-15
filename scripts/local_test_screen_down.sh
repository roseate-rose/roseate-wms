#!/usr/bin/env bash

set -euo pipefail

SCREEN_NAME="${SCREEN_NAME:-roseate-wms}"

# `screen -list` returns exit code 1 even when sessions exist, so we must ignore it.
sessions="$((screen -list 2>/dev/null || true) | awk -v name="${SCREEN_NAME}" '$1 ~ ("\\." name "$") {print $1}')"

if [[ -z "${sessions}" ]]; then
  echo "screen session '${SCREEN_NAME}' not found."
  exit 0
fi

echo "Stopping screen session(s) for '${SCREEN_NAME}':"
echo "${sessions}" | sed 's/^/  - /'

while IFS= read -r sid; do
  [[ -z "${sid}" ]] && continue
  screen -S "${sid}" -X quit || true
done <<< "${sessions}"

echo "Stopped."
