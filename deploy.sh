#!/usr/bin/env bash

set -euo pipefail

APP_NAME="${APP_NAME:-roseate-wms}"
VOLUME_NAME="${VOLUME_NAME:-roseate_storage}"
VOLUME_REGION="${VOLUME_REGION:-sin}"
VOLUME_SIZE="${VOLUME_SIZE:-1}"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "flyctl is required. Install it from https://fly.io/docs/hands-on/install-flyctl/"
  exit 1
fi

if [[ ! -f "fly.toml" ]]; then
  echo "fly.toml not found. Run this script from the project root."
  exit 1
fi

echo "Checking Fly volume ${VOLUME_NAME} for app ${APP_NAME}..."
existing_count="$(flyctl volumes list -a "${APP_NAME}" | awk -v name="${VOLUME_NAME}" 'NR>1 && $3==name {c++} END {print c+0}')"
if [[ "${existing_count}" -eq 0 ]]; then
  echo "Creating volume ${VOLUME_NAME} in region ${VOLUME_REGION} (${VOLUME_SIZE}GB)..."
  flyctl volumes create "${VOLUME_NAME}" --app "${APP_NAME}" --region "${VOLUME_REGION}" --size "${VOLUME_SIZE}" --yes
elif [[ "${existing_count}" -eq 1 ]]; then
  echo "Volume ${VOLUME_NAME} already exists; skipping create."
else
  echo "Multiple volumes named ${VOLUME_NAME} exist for ${APP_NAME}. Refusing to create another."
  flyctl volumes list -a "${APP_NAME}"
  exit 1
fi

echo "Deploying ${APP_NAME}..."
flyctl deploy --app "${APP_NAME}" --yes --remote-only --depot=false

cat <<'EOF'

If you have not set a JWT secret yet, run:

  flyctl secrets set JWT_SECRET_KEY='replace-with-a-long-random-secret' --app roseate-wms

EOF
