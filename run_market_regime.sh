#!/bin/bash
# Market regime detection runner

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/YoloInvest"
cd "$SCRIPT_DIR"
source venv/bin/activate

if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Missing TELEGRAM_BOT_TOKEN"
  exit 1
fi

PHASE="${1:-初判}"

pip install -r requirements.txt >/tmp/yoloinvest-regime-pip.log 2>&1
python3 -m yoloinvest.market_regime.cli scheduled --phase "$PHASE"
