# YoloInvest 市场简报系统

自动化市场分析和简报生成系统。

## 功能

- 📈 **股票监控**（科技巨头、芯片、数据中心、电力、稀土）
- 💰 **加密货币**（BTC、ETH）
- 🛢️ **大宗商品**（原油、黄金、铜、白银、天然气）
- 📰 **新闻抓取与 AI 分析**
- 📅 **财报日历**
- 📊 **经济数据日历**
- 📬 **自动发送到 Telegram 群**

## 自动运行

每天西雅图时间早上 6:00 自动生成并发送简报。

当前调度方式：
- 使用 **OpenClaw cron**
- 不使用 systemd timer，避免和 OpenClaw gateway 冲突

## 手动运行

```bash
cd ~/.openclaw/workspace/market-briefing
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_CHAT_ID='...'
export LLM_API_KEY='...'
# 可选
export LLM_API_BASE='https://api.tabcode.cc/claude/kiropower'
export LLM_MODEL='claude-sonnet-4-5-20250929'
./run_briefing.sh
```

## 环境变量

必需：

- `TELEGRAM_BOT_TOKEN` - Telegram Bot token
- `TELEGRAM_CHAT_ID` - Telegram 群组或会话 ID
- `LLM_API_KEY` - Claude 兼容接口 API key

可选：

- `LLM_API_BASE` - Claude 兼容接口基础地址
  - 默认：`https://api.tabcode.cc/claude/kiropower`
- `LLM_MODEL` - 分析模型名
  - 默认：`claude-sonnet-4-5-20250929`

## 项目结构

```text
market-briefing/
├── README.md             # 项目说明
├── ReleaseNote.md        # 发布记录与变更日志
├── main.py               # 主入口，串联抓数、分析、生成
├── run_briefing.sh       # 一键运行主流程并发送结果
├── config.py             # 全局配置（环境变量、标的、路径等）
├── models.py             # 数据模型定义
├── fetchers.py           # 统一数据抓取层
├── analyzers.py          # AI 分析层（Claude 兼容接口）
├── generators.py         # 文本简报生成器
├── sender.py             # Telegram 发送器
├── fetch_data.py         # 抓取市场数据的轻量包装脚本
├── fetch_news.py         # 抓取新闻的独立脚本
├── fetch_earnings.py     # 抓取财报数据的独立脚本
├── fetch_economic.py     # 抓取经济数据的独立脚本
├── analyze_news.py       # 兼容旧流程的分析包装脚本
├── analyze_market.py     # 兼容旧流程的生成包装脚本
├── generate_image.py     # 生成图片版简报
├── fonts/                # 中文字体资源
├── __pycache__/          # Python 缓存
└── venv/                 # Python 虚拟环境
```

## 当前数据口径

股票、加密货币和大宗商品目前统一使用 **纯日线口径**：

- `price` = 最近一个完整交易日的收盘价
- `previous_close` = 前一个完整交易日的收盘价
- `change_percent` = 两个完整交易日收盘价之间的涨跌幅
- `volume` = 最近一个完整交易日的总成交量
- `price_date` = 本次报告实际采用的收盘日期
- `previous_close_date` = 本次涨跌幅对比所用的上一交易日日期

生成后的报告末尾会直接写明：
- 本报告价格采用哪一天的收盘价
- 涨跌幅是相对哪一天的收盘价计算
- 成交量采用哪一天的总成交量

## AI 分析接口

当前使用 Claude 兼容接口：

- Base URL: `https://api.tabcode.cc/claude/kiropower`
- Messages URL: `https://api.tabcode.cc/claude/kiropower/v1/messages`

## 输出文件

流程运行时会把中间结果写到 `/tmp`：

- `/tmp/market_data.json`
- `/tmp/market_news.json`
- `/tmp/earnings_calendar.json`
- `/tmp/economic_data.json`
- `/tmp/news_analysis.txt`
- `/tmp/detailed.txt`

## 备注

- `LYNAS.AX` 已从稀土 watchlist 中移除，因为 Yahoo Finance 返回不稳定
- 文本简报链路已验证可用，Telegram 发送正常
- 旧脚本仍保留为 wrapper，避免打断已有使用方式，但核心逻辑已集中到 `fetchers.py`、`analyzers.py`、`generators.py`

---

**YoloInvest** - Powered by OpenClaw & Claude AI
