#!/bin/bash
# YoloInvest weekly economic calendar push

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/YoloInvest"

cd "$SCRIPT_DIR"
source venv/bin/activate

if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

export TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID_MARKET_BRIEFING"

python3 -m yoloinvest.weekly_calendar.app
