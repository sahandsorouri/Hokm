#!/usr/bin/env bash
# Deploy or update the Hokm bot on a Linux server with systemd.
#
# Usage (first time):
#   REPO_URL=https://github.com/<user>/Hokm.git ./deploy/deploy.sh
# Subsequent updates: just run ./deploy/deploy.sh from the app dir.

set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/hokm-bot}"
REPO_URL="${REPO_URL:-}"
SERVICE_NAME="hokm-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
RUN_USER="${SUDO_USER:-$USER}"

echo "▶ Deploying Hokm bot for user: $RUN_USER"
echo "▶ App dir: $APP_DIR"

# 1. clone or pull
if [ ! -d "$APP_DIR/.git" ]; then
  if [ -z "$REPO_URL" ]; then
    echo "❌ $APP_DIR is not a git repo. Pass REPO_URL=... to clone."
    exit 1
  fi
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

# 2. python venv + deps
if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  .env created from template. Edit it and set BOT_TOKEN, then re-run."
  exit 0
fi
if grep -q "replace-with-token" .env; then
  echo "⚠️  .env still has placeholder token. Edit it before starting service."
  exit 0
fi

# 4. data dir + log
mkdir -p data
touch data/bot.log

# 5. install systemd unit
TMP_UNIT=$(mktemp)
sed -e "s|__USER__|$RUN_USER|g" -e "s|__APP_DIR__|$APP_DIR|g" \
    deploy/hokm-bot.service > "$TMP_UNIT"
sudo cp "$TMP_UNIT" "$SERVICE_FILE"
rm -f "$TMP_UNIT"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "✅ Deployed."
echo "  status:  sudo systemctl status $SERVICE_NAME"
echo "  logs:    tail -f $APP_DIR/data/bot.log"
echo "  restart: sudo systemctl restart $SERVICE_NAME"
