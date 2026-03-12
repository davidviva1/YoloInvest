#!/bin/bash
# YoloInvest market briefing runner

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/YoloInvest"

cd "$SCRIPT_DIR"
source venv/bin/activate
pip install -r requirements.txt >/tmp/yoloinvest-market-briefing-pip.log 2>&1

if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

required_vars=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID_MARKET_BRIEFING
  LLM_API_KEY
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name}" ]; then
    echo "Missing required environment variable: $var_name"
    exit 1
  fi
done

export TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID_MARKET_BRIEFING"

python3 -m yoloinvest.market_briefing.app
python3 - <<'PY'
from yoloinvest.common.sender import TelegramSender
sender = TelegramSender()
if sender.send_report():
    print('✅ Report sent successfully!')
else:
    raise SystemExit('❌ Failed to send report')
PY
