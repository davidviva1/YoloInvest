#!/bin/bash
# YoloInvest Market Briefing - 主流程脚本

set -e

SCRIPT_DIR="$HOME/.openclaw/workspace/YoloInvest"

cd "$SCRIPT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 安装锁定依赖，确保手动运行和 cron 使用同一套环境
pip install -r requirements.txt >/tmp/yoloinvest-market-briefing-pip.log 2>&1

# 加载本地环境变量文件，方便 cron/后台任务复用同一套配置
if [ -f "$SCRIPT_DIR/.env.market-briefing" ]; then
  set -a
  source "$SCRIPT_DIR/.env.market-briefing"
  set +a
fi

# 检查关键环境变量
required_vars=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  LLM_API_KEY
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name}" ]; then
    echo "Missing required environment variable: $var_name"
    exit 1
  fi
done

# 运行主程序
python3 main.py

# 发送简报到 Telegram
python3 sender.py
