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
if ! flyctl volumes list -a "${APP_NAME}" | awk 'NR>1 {print $1}' | grep -Fxq "${VOLUME_NAME}"; then
  echo "Creating volume ${VOLUME_NAME} in region ${VOLUME_REGION} (${VOLUME_SIZE}GB)..."
  flyctl volumes create "${VOLUME_NAME}" --app "${APP_NAME}" --region "${VOLUME_REGION}" --size "${VOLUME_SIZE}" --yes
else
  echo "Volume ${VOLUME_NAME} already exists."
fi

echo "Deploying ${APP_NAME}..."
flyctl deploy --app "${APP_NAME}" --yes

cat <<'EOF'

If you have not set a JWT secret yet, run:

  flyctl secrets set JWT_SECRET_KEY='replace-with-a-long-random-secret' --app roseate-wms

EOF
