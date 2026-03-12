#!/bin/bash
# Intraday mega-cap tech alert runner

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/market-briefing"

cd "$SCRIPT_DIR"
source venv/bin/activate

if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

required_vars=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name}" ]; then
    echo "Missing required environment variable: $var_name"
    exit 1
  fi
done

pip install -r requirements.txt >/tmp/options-alert-pip.log 2>&1
python options_alert.py
