#!/bin/bash
# Swing alert runner for leveraged ETFs

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/YoloInvest"

cd "$SCRIPT_DIR"
source venv/bin/activate

if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

required_vars=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID_OPTIONS_ALERT
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name}" ]; then
    echo "Missing required environment variable: $var_name"
    exit 1
  fi
done

export TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID_OPTIONS_ALERT"

pip install -r requirements.txt >/tmp/yoloinvest-swing-alert-pip.log 2>&1
python3 -m yoloinvest.swing_alert.swing
